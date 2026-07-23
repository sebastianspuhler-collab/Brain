"""LLM-gestützte Kundenstatus-Synthese (Sebastian, 2026-07-20: "kein Raten,
keine Fehlinterpretation" - Transkripte, E-Mails und Termine sind alle Input
für den Kundenstatus, nicht nur Ordner-Anwesenheit).

Liest alle bereits abgelegten Dokument-/Meeting-Zusammenfassungen eines Kunden
(die classify.py beim Einsortieren schon per LLM extrahiert hat - hier keine
neue Extraktion, nur Synthese) und leitet daraus einen begründeten Status ab.

Zwei Sicherungen gegen Halluzination:
1. Floor: harte Ordner-Fakten (Vertrag vorhanden -> mindestens "auftrag") sind
   ein Mindest-Status, den das LLM nie unterschreiten darf.
2. Zitatzwang: jede Begründung muss sich auf konkrete Dateinamen stützen: die
   werden gegen die tatsächlich vorhandenen Dateien geprüft - erfundene
   Quellen senken die Sicherheit auf "niedrig" statt unbemerkt durchzugehen.

Ergebnis wird pro Kunde gecacht (_agent/kunden_status_cache.json) und nur bei
geändertem Dateibestand, geänderter Notiz oder geändertem nächsten Termin neu
berechnet - kein neues (potenziell abweichendes) Urteil bei jedem
Dashboard-Aufruf. Sebastians Notiz fließt zusätzlich als Steuerungs-Hinweis in
den Prompt ein, nicht nur als Anzeige-Text."""
import hashlib
import json
import re
from pathlib import Path

from app.config import get_settings
from app.constants import Models
from app.services.anthropic_client import complete_json

STATUS_RANK = {
    "neuer_kontakt": 0, "erstgespraech": 1, "angebotsphase": 2,
    "auftrag": 3, "fulfillment": 4, "abgeschlossen": 5,
}
_DOKUMENT_ORDNER = ("Vertraege", "Angebote", "Meetings", "Dokumente", "Praesentationen")
_MAX_DOKUMENTE = 25  # Kontextlimit - neueste zuerst
_MEETING_FELDER = (
    ("kernpunkte", "Kernpunkte"), ("zusagen", "Zusagen"),
    ("naechste_schritte", "Nächste Schritte"), ("entscheidungen", "Entscheidungen"),
)

_FALLBACK = {
    "status": "neuer_kontakt", "sicherheit": "niedrig",
    "begruendung": "Automatische Bewertung nicht verfügbar, Anzeige basiert nur auf Ordnerstruktur.",
    "quellen": [], "warnsignal": None,
    # ist_relevant=True im Zweifel - lieber fälschlich anzeigen als fälschlich
    # verstecken, wenn die Bewertung selbst schon fehlgeschlagen ist.
    "ist_relevant": True, "relevanz_begruendung": "",
    "anzeige_name": "", "aktueller_stand": "",
}


def _cache_path() -> Path:
    return get_settings().agent_dir / "kunden_status_cache.json"


def _load_cache() -> dict:
    path = _cache_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(data: dict) -> None:
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _hat_dateien(ordner: Path) -> bool:
    return ordner.exists() and any(f.is_file() for f in ordner.glob("*"))


def _floor_status(kunde_path: Path) -> str:
    """Deterministisch aus Ordner-Anwesenheit - siehe Moduldoc. Wird vom LLM
    nie unterschritten, unabhängig davon wie unklar der Inhalt wirkt.

    Leads sind eine einzelne .md-Datei statt eines Kundenordners (keine
    Vertraege/Angebote/Meetings-Unterordner) - Floor dafür reicht die alte
    Byte-Größen-Heuristik aus dashboard.py: eine reine Kalender-Stub-Notiz
    (siehe calendar_lead_service._write_lead_stub) ist konstant kurz."""
    if kunde_path.is_file():
        return "erstgespraech" if kunde_path.stat().st_size > 800 else "neuer_kontakt"
    if _hat_dateien(kunde_path / "Vertraege"):
        return "auftrag"
    if _hat_dateien(kunde_path / "Angebote"):
        return "angebotsphase"
    if _hat_dateien(kunde_path / "Meetings"):
        return "erstgespraech"
    return "neuer_kontakt"


def _abschnitt(text: str, titel: str) -> str:
    m = re.search(rf"## {titel}\n(.*?)(?:\n##|\Z)", text, re.S)
    if not m:
        return ""
    zeilen = [z.lstrip("- ").strip() for z in m.group(1).strip().splitlines() if z.strip()]
    zeilen = [z for z in zeilen if z and z != "(keine)"]
    return "; ".join(zeilen)


def _lies_dokument(f: Path, ordner: str) -> dict | None:
    try:
        text = f.read_text(encoding="utf-8")
    except Exception:
        return None
    m_datum = re.search(r"^datum:\s*(\d{4}-\d{2}-\d{2})", text, re.M)
    m_kat = re.search(r"^kategorie:\s*(.+)$", text, re.M)
    m_zus = re.search(r"## Zusammenfassung\n(.*?)(?:\n##|\Z)", text, re.S)
    eintrag = {
        "datei": f.name,
        "ordner": ordner,
        "datum": m_datum.group(1) if m_datum else "",
        "kategorie": m_kat.group(1).strip() if m_kat else "",
        "zusammenfassung": m_zus.group(1).strip() if m_zus else "",
    }
    if ordner == "Meetings":
        for feld, titel in _MEETING_FELDER:
            wert = _abschnitt(text, titel)
            if wert:
                eintrag[feld] = wert
    return eintrag


def _sammle_dokumente(kunde_path: Path) -> list[dict]:
    """Liest Frontmatter + Zusammenfassung/Meeting-Abschnitte aller bereits
    abgelegten .md-Dateien - reine Wiederverwendung dessen, was classify.py /
    extract_meeting_structure() beim Einsortieren bereits per LLM
    herausgezogen und in die Datei geschrieben hat, keine neue Extraktion.

    Leads sind eine einzelne .md-Datei in Leads/ statt eines Kundenordners
    mit Unterordnern - dafür wird nur diese eine Datei plus ein optionaler
    "<Name>-Korrespondenz/"-Ordner daneben gelesen (E-Mails, die
    email_indexer._write_lead_correspondence() dem Lead zugeordnet hat -
    Sebastian, 2026-07-21: der Stand soll auch aus laufender Korrespondenz
    kommen, nicht nur aus dem einmaligen Erstgesprächs-Protokoll)."""
    if kunde_path.is_file():
        dokumente = []
        eintrag = _lies_dokument(kunde_path, "Leads")
        if eintrag:
            dokumente.append(eintrag)
        lead_name = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", kunde_path.stem)
        korr_dir = kunde_path.parent / f"{lead_name}-Korrespondenz"
        if korr_dir.exists():
            for f in korr_dir.glob("*.md"):
                korr_eintrag = _lies_dokument(f, "Korrespondenz")
                if korr_eintrag:
                    dokumente.append(korr_eintrag)
        dokumente.sort(key=lambda d: d["datum"], reverse=True)
        return dokumente[:_MAX_DOKUMENTE]

    dokumente = []
    for sub in _DOKUMENT_ORDNER:
        ordner = kunde_path / sub
        if not ordner.exists():
            continue
        for f in ordner.glob("*.md"):
            eintrag = _lies_dokument(f, sub)
            if eintrag:
                dokumente.append(eintrag)
    dokumente.sort(key=lambda d: d["datum"], reverse=True)
    return dokumente[:_MAX_DOKUMENTE]


def _input_hash(dokumente: list[dict], notiz: str, naechster_termin: dict | None) -> str:
    basis = json.dumps(
        {
            "d": [(d["datei"], d["datum"]) for d in dokumente],
            "n": notiz,
            "t": naechster_termin.get("start") if naechster_termin else None,
        },
        sort_keys=True,
    )
    return hashlib.sha256(basis.encode()).hexdigest()[:16]


def _digest(dokumente: list[dict]) -> str:
    bloecke = []
    for d in dokumente:
        zeilen = [f"[{d['datum'] or '?'}] {d['ordner']}/{d['datei']} ({d['kategorie']})"]
        if d.get("zusammenfassung"):
            zeilen.append(f"  Zusammenfassung: {d['zusammenfassung']}")
        for feld, label in _MEETING_FELDER:
            if d.get(feld):
                zeilen.append(f"  {label}: {d[feld]}")
        bloecke.append("\n".join(zeilen))
    return "\n\n".join(bloecke)


def bewerte_kunde(
    kunde_path: Path, notiz: str = "", naechster_termin: dict | None = None, kunde_name: str = "",
) -> dict:
    dokumente = _sammle_dokumente(kunde_path)
    floor = _floor_status(kunde_path)
    dateinamen = {d["datei"] for d in dokumente}

    if not dokumente:
        return {
            "status": floor,
            "sicherheit": "hoch" if floor == "neuer_kontakt" else "mittel",
            "begruendung": "Keine inhaltlichen Unterlagen vorhanden, Einschätzung rein aus Ordnerstruktur.",
            "quellen": [], "warnsignal": None,
            "ist_relevant": True, "relevanz_begruendung": "",
            "anzeige_name": kunde_name, "aktueller_stand": "",
        }

    termin_text = (
        f"Nächster Termin: {naechster_termin['titel']} am {naechster_termin['start']}"
        if naechster_termin else "Kein bevorstehender Termin bekannt."
    )
    notiz_text = f'\nHinweis von Sebastian (unbedingt berücksichtigen): "{notiz.strip()}"\n' if notiz.strip() else ""

    prompt = f"""Du bewertest den Vertriebs-/Betreuungsstatus eines Kunden für Prozessia GbR
anhand ALLER vorliegenden Unterlagen (E-Mails, Dokumente, Meeting-Mitschriften).

Ordner-/Dateiname im Vault: "{kunde_name}"

Chronologie (neueste zuerst):
{_digest(dokumente)}

{termin_text}
{notiz_text}
Mindest-Status aus harten Fakten (Vertrag/Angebot/Meeting-Ordner tatsächlich vorhanden): "{floor}"
Dieser Mindest-Status darf NIEMALS unterschritten werden, auch wenn der
Inhalt unklar wirkt - er basiert auf tatsächlich vorhandenen Dateien, nicht
auf Interpretation.

Mögliche Status (aufsteigend): neuer_kontakt, erstgespraech, angebotsphase, auftrag, fulfillment, abgeschlossen

Bestimme:
1. status: einer der Werte oben, mindestens "{floor}"
2. sicherheit: "hoch" (eindeutige, aktuelle Belege), "mittel" (plausibel, aber lückenhaft oder älter) oder "niedrig" (widersprüchlich oder kaum Belege)
3. begruendung: 1-2 deutsche Sätze, MUSS sich auf konkrete Dateien aus der Chronologie oben beziehen (Dateiname nennen)
4. quellen: JSON-Array der Dateinamen (exakt wie oben, nur der Dateiname nach dem "/"), auf die sich die Begründung stützt
5. warnsignal: kurzer deutscher Satz, falls ein Alarmzeichen erkennbar ist (z.B. lange Funkstille nach Angebot, abgesagter Termin, erkennbare Unzufriedenheit, überfälliges Follow-up) - sonst null
6. ist_relevant: true/false - handelt es sich hier wirklich um eine Kunden- oder Interessenten-Beziehung für Prozessia? false bei: externen Lieferanten/Subunternehmern/IT-Dienstleistern, die nur im Rahmen eines ANDEREN Kundenprojekts auftauchen; privaten oder themenfremden Inhalten ohne Geschäftsbezug; Newslettern, Spam oder generischen Massenmails, die nur zufällig hier abgelegt wurden
7. relevanz_begruendung: 1 kurzer deutscher Satz, warum (nur ausfüllen wenn ist_relevant=false, sonst leer lassen)
8. anzeige_name: der echte Firmen- oder Personenname aus dem Inhalt (z.B. "Forlin GmbH"), falls klar erkennbar - sonst einfach "{kunde_name}" übernehmen. NIEMALS einen Namen erfinden, der nirgends in der Chronologie steht.
9. aktueller_stand: 1 kurzer deutscher Satz, was gerade der Stand ist bzw. der nächste Schritt - aus der GESAMTEN Chronologie, nicht nur dem neuesten Dokument. Leer lassen wenn nicht erkennbar.

Antworte NUR als JSON, keine Erklärung. Format:
{{"status": "...", "sicherheit": "...", "begruendung": "...", "quellen": [...], "warnsignal": "..." oder null, "ist_relevant": true/false, "relevanz_begruendung": "...", "anzeige_name": "...", "aktueller_stand": "..."}}"""

    try:
        raw = complete_json(prompt, model=Models.SONNET, max_tokens=700).strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
    except Exception:
        return {**_FALLBACK, "status": floor, "anzeige_name": kunde_name}

    status = result.get("status")
    if status not in STATUS_RANK:
        status = floor
    sicherheit = result.get("sicherheit")
    if sicherheit not in ("hoch", "mittel", "niedrig"):
        sicherheit = "mittel"

    quellen_roh = [q for q in result.get("quellen", []) if isinstance(q, str)]
    quellen_valide = [q for q in quellen_roh if q in dateinamen]
    if len(quellen_valide) < len(quellen_roh):
        # LLM hat eine nicht existierende Datei zitiert - klassisches
        # Halluzinations-Symptom, Sicherheit entsprechend herabstufen.
        sicherheit = "niedrig"

    if STATUS_RANK[status] < STATUS_RANK[floor]:
        # Floor hat Vorrang vor Interpretation - ein unterschrittener Floor
        # bedeutet, das LLM hat vorhandene Belege ignoriert.
        status = floor
        sicherheit = "niedrig"

    anzeige_name = result.get("anzeige_name")
    if not isinstance(anzeige_name, str) or not anzeige_name.strip():
        anzeige_name = kunde_name

    return {
        "status": status,
        "sicherheit": sicherheit,
        "begruendung": result.get("begruendung", ""),
        "quellen": quellen_valide,
        "warnsignal": result.get("warnsignal") or None,
        "ist_relevant": bool(result.get("ist_relevant", True)),
        "relevanz_begruendung": result.get("relevanz_begruendung") or "",
        "anzeige_name": anzeige_name.strip(),
        "aktueller_stand": (result.get("aktueller_stand") or "").strip(),
    }


def get_status(
    kunde_name: str, kunde_path: Path, notiz: str = "",
    naechster_termin: dict | None = None, force: bool = False,
) -> dict:
    dokumente = _sammle_dokumente(kunde_path)
    input_hash = _input_hash(dokumente, notiz, naechster_termin)
    cache = _load_cache()
    cached = cache.get(kunde_name)

    if not force and cached and cached.get("input_hash") == input_hash:
        return cached["ergebnis"]

    ergebnis = bewerte_kunde(kunde_path, notiz, naechster_termin, kunde_name)
    cache[kunde_name] = {"input_hash": input_hash, "ergebnis": ergebnis}
    _save_cache(cache)
    return ergebnis
