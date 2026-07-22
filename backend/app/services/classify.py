"""Inbox-Verarbeitung: Dateien klassifizieren, Text extrahieren, ablegen.
Migriert aus _agent/heartbeat.py. Als importierbares Modul statt Subprocess-Aufruf,
damit der Chat-Endpoint (/api/inbox_process) es direkt callen kann statt einen
neuen Python-Prozess zu starten.
"""
import json
import re
import shutil
from datetime import date, datetime
from pathlib import Path

from app.config import get_settings
from app.constants import Models
from app.services.anthropic_client import complete_json

SKIP_EXTENSIONS = {
    ".js", ".ts", ".map", ".mjs", ".jsx", ".tsx", ".css",
    ".yml", ".yaml", ".eslintrc", ".nycrc", ".npmignore",
    ".enc", ".lock", ".editorconfig", ".orig",
}
SKIP_NAMES = {
    "Thumbs.db", ".DS_Store", "package-lock.json", "package.json",
    "tsconfig.json", "tsdoc-metadata.json", "openai",
}
SKIP_PREFIXES = ("README", "readme", "LICENSE", "license", "CHANGELOG",
                  "HISTORY", "History", "CONTRIBUTING", "contributing")
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".mp4", ".mov", ".mp3"}


def _cache_path() -> Path:
    return get_settings().agent_dir / "logs" / "processed_cache.json"


def _load_cache() -> set:
    path = _cache_path()
    if path.exists():
        try:
            return set(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            return set()
    return set()


def _save_cache(cache: set) -> None:
    _cache_path().write_text(json.dumps(list(cache)), encoding="utf-8")


def _extract_pdf_via_mistral_ocr(filepath: Path, max_chars: int) -> str | None:
    """OCR-Vorstufe für PDFs (Umsetzungsplan-Memo 2026-07-16, Punkt C1): Mistral
    liest gescannte/mehrspaltige PDFs zuverlässiger als die reine PyPDF2-
    Textextraktion aus - genau das Problem, das in diesem Projekt wiederholt zu
    abgeschnittenen/lückenhaften .md-Extrakten geführt hat. Gibt None zurück,
    wenn irgendetwas schiefgeht (kein Key, Netzwerkfehler, unerwartete Antwort) -
    der Aufrufer fällt dann automatisch auf PyPDF2 zurück, siehe extract_text()."""
    settings = get_settings()
    if not settings.mistral_api_key:
        return None
    try:
        import base64
        import requests

        b64 = base64.b64encode(filepath.read_bytes()).decode("ascii")
        resp = requests.post(
            "https://api.mistral.ai/v1/ocr",
            headers={"Authorization": f"Bearer {settings.mistral_api_key}"},
            json={
                "model": "mistral-ocr-latest",
                "document": {
                    "type": "document_url",
                    "document_url": f"data:application/pdf;base64,{b64}",
                },
            },
            timeout=60,
        )
        resp.raise_for_status()
        pages = resp.json().get("pages", [])
        text = "\n\n".join(p.get("markdown", "") for p in pages).strip()
        return text[:max_chars] if text else None
    except Exception:
        return None


def extract_text(filepath: Path, max_chars: int = 3000) -> str | None:
    suffix = filepath.suffix.lower()
    try:
        if suffix == ".pdf":
            ocr_text = _extract_pdf_via_mistral_ocr(filepath, max_chars)
            if ocr_text:
                return ocr_text

            import PyPDF2

            with open(filepath, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return " ".join(page.extract_text() or "" for page in reader.pages)[:max_chars]
        if suffix == ".docx":
            from docx import Document

            doc = Document(filepath)
            return " ".join(p.text for p in doc.paragraphs)[:max_chars]
        if suffix in (".xlsx", ".xls"):
            import openpyxl

            wb = openpyxl.load_workbook(filepath, read_only=True)
            text = []
            for ws in wb.worksheets:
                for row in ws.iter_rows(values_only=True):
                    text.append(" ".join(str(c) for c in row if c))
            return " ".join(text)[:max_chars]
        if suffix in (".pptx", ".ppt"):
            from pptx import Presentation

            prs = Presentation(filepath)
            text = []
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text.append(shape.text)
            return " ".join(text)[:max_chars]
        if suffix == ".html":
            from html.parser import HTMLParser

            class TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.parts: list[str] = []

                def handle_data(self, data):
                    self.parts.append(data)

            p = TextExtractor()
            p.feed(filepath.read_text(encoding="utf-8", errors="ignore"))
            return " ".join(p.parts)[:max_chars]
        if suffix == ".json":
            raw = filepath.read_text(encoding="utf-8", errors="ignore")[:max_chars]
            return f"[JSON-Datei] {raw}"
        if suffix in (".txt", ".md", ".markdown", ".csv"):
            return filepath.read_text(encoding="utf-8", errors="ignore")[:max_chars]
        if suffix in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"):
            return "[Bilddatei, kein Text extrahierbar]"
        if suffix in (".mp4", ".mov", ".avi", ".mkv", ".mp3"):
            return "[Mediendatei, kein Text extrahierbar]"
        if suffix == ".zip":
            return "[ZIP-Archiv]"
        return f"[Unbekanntes Format: {suffix}]"
    except Exception:
        return None


def list_customer_names() -> list[str]:
    """Ordnernamen unter Kunden/ (ohne Platzhalter/Vorlage) - Basis für die
    automatische Zuordnung von E-Mails zu bestehenden Kunden."""
    kunden_dir = get_settings().vault_path / "Kunden"
    if not kunden_dir.exists():
        return []
    return [
        p.name for p in sorted(kunden_dir.iterdir())
        if p.is_dir() and not p.name.startswith((".", "[", "_"))
    ]


def list_lead_names() -> list[str]:
    """Dateinamen (ohne Datumspräfix) unter Leads/ - analoge Basis für die
    automatische Zuordnung von E-Mails zu Leads (siehe list_customer_names())."""
    leads_dir = get_settings().vault_path / "Leads"
    if not leads_dir.exists():
        return []
    return [
        re.sub(r"^\d{4}-\d{2}-\d{2}-", "", p.stem) for p in sorted(leads_dir.glob("*.md"))
    ]


def _scan_vault_folders() -> str:
    """Liest die aktuelle Ordnerstruktur des Vault dynamisch aus (Port aus
    _agent/heartbeat.py), statt einer hartcodierten Zielordner-Liste — damit
    neue Kunden und Unterordner (z.B. Meetings/Dokumente) automatisch bekannt sind."""
    settings = get_settings()
    lines = []
    for top in sorted(settings.vault_path.iterdir()):
        if top.name.startswith(".") or top.name.startswith("_") or not top.is_dir():
            continue
        if top.name in ("backend", "frontend", "Uni"):
            continue
        subs = sorted(p.name for p in top.iterdir() if p.is_dir() and not p.name.startswith("."))
        if subs:
            for sub in subs:
                subsubs = sorted(p.name for p in (top / sub).iterdir() if p.is_dir() and not p.name.startswith("."))
                if subsubs:
                    for ss in subsubs:
                        lines.append(f"- {top.name}/{sub}/{ss}")
                else:
                    lines.append(f"- {top.name}/{sub}")
        else:
            lines.append(f"- {top.name}")
    return "\n".join(lines)


def _load_memory_rules() -> str:
    settings = get_settings()
    if not settings.memory_path.exists():
        return ""
    lines = []
    in_section = False
    for line in settings.memory_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## REGEL") or line.startswith("## PROZESS"):
            in_section = True
        elif line.startswith("## ") and in_section:
            in_section = False
        elif in_section and line.startswith("- "):
            lines.append(line)
    return "\n".join(lines)


def classify(filepath: Path, content: str) -> dict | None:
    settings = get_settings()
    relative = filepath.relative_to(settings.inbox_dir)
    ordner_kontext = str(relative.parent) if str(relative.parent) != "." else ""
    memory_rules = _load_memory_rules()
    vault_struktur = _scan_vault_folders()

    prompt = f"""Du sortierst Dokumente für Prozessia GbR (KI-Agentur, Saarbrücken) ein.

Dateiname: {filepath.name}
Inbox-Unterordner: {ordner_kontext or "keiner"}
Inhalt (Auszug): {content}

{f"Gelernte Ablageregeln:{chr(10)}{memory_rules}{chr(10)}" if memory_rules else ""}
Aktuelle Vault-Struktur (alle existierenden Ordner):
{vault_struktur}

REGELN:
- Kundendokumente → Kunden/[Kundenname]/[Unterordner]
  Unterordner-Logik:
  · Vertraege/   → NDA, AVV, SLA, Bestellungen, Rechnungen, Auftragsbestätigungen
  · Angebote/    → Angebote, Kostenkalkulationen, Wartungsmodelle, Preislisten
  · Meetings/    → Besprechungen, Protokolle, Mitschriften, Meet-Aufzeichnungen
  · Praesentationen/ → Präsentationen, Pitches, Slides
  · Dokumente/   → alles andere (Specs, Fachkonzepte, Anleitungen, Projektpläne)
- Neuer Kunde erkannt → zielordner: "Kunden/[Firmenname]/Dokumente" (Ordner wird automatisch erstellt)
  ACHTUNG neuer_kunde=true nur bei einer ECHTEN neuen Kunden-/Interessenten-Beziehung
  für Prozessia selbst. KEIN neuer Kunde ist z.B.: ein externer Lieferant/
  Subunternehmer/IT-Dienstleister, der nur im Rahmen eines BESTEHENDEN
  Kundenprojekts erwähnt wird (der gehört zu diesem bestehenden Kunden, nicht
  in einen eigenen Ordner); eine private oder thematisch fremde Person/Inhalt
  ohne Geschäftsbezug zu Prozessia; ein Newsletter, eine Werbe-Mail oder
  generische Massenkommunikation, in der zufällig ein Name auftaucht. Im
  Zweifel eher zu Memos/ oder zum bereits bestehenden Kunden einordnen als
  einen neuen Kundenordner zu erfinden.
- Verträge die keinen Kunden zugeordnet werden können → Vertraege/
- Leads → Leads/
- Finanzen → Finanzen/Rechnungen oder Finanzen/Angebote
- Marketing → Marketing/[passender Unterordner]
- Sales → Sales/[passender Unterordner]

Bestimme:
1. kategorie: Kunde/Lead/Produkt/Vertrag/Marketing/Sales/Finanzen/Memo
2. zusammenfassung: 2-3 Sätze was das Dokument enthält (bei Medien: kurze Beschreibung)
3. tags: 3-5 relevante Tags als JSON-Array
4. zielordner: exakter relativer Pfad (darf neu sein, wird erstellt)
5. neuer_kunde: true/false (ob ein bisher unbekannter Kunde erkannt wurde)

Antworte NUR als JSON, keine Erklärung."""

    try:
        # thinking explizit deaktiviert (Bug 2026-07-17): ohne das kann das Modell
        # einen Teil des knappen max_tokens-Budgets fürs Nachdenken verbrauchen und
        # die eigentliche JSON-Antwort abschneiden (stop_reason "max_tokens" mit
        # leerem/kaputtem Text-Block) - genau das ließ z.B. das TPG-Transkript als
        # "API-Klassifizierung fehlgeschlagen" durchfallen, obwohl der Aufruf an
        # sich funktioniert hätte.
        raw = complete_json(prompt, model=Models.SONNET, max_tokens=500).strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        if result.get("neuer_kunde"):
            ziel = settings.vault_path / result.get("zielordner", "Memos")
            kunde_root = ziel.parent if ziel.name in ("Vertraege", "Angebote", "Dokumente", "Meetings", "Praesentationen") else ziel
            for sub in ("Vertraege", "Angebote", "Dokumente", "Meetings"):
                (kunde_root / sub).mkdir(parents=True, exist_ok=True)
        return result
    except Exception:
        return None


def extract_meeting_structure(filepath: Path) -> dict | None:
    """Extrahiert Teilnehmer/Kernpunkte/Zusagen/Nächste Schritte aus einem
    Meeting-Transkript. Liest die Datei mit größerem max_chars erneut ein,
    damit auch spät im Gespräch genannte Zusagen/nächste Schritte erfasst
    werden (die reguläre Klassifizierung kappt bei 3000 Zeichen)."""
    content = extract_text(filepath, max_chars=20000)
    if not content:
        return None

    prompt = f"""Das ist das Transkript eines Kundengesprächs für Prozessia GbR.

Transkript:
{content}

Extrahiere:
1. teilnehmer: Namen der Gesprächsteilnehmer als JSON-Array (kurz, ohne Rollen/Firmen falls nicht eindeutig erkennbar)
2. kernpunkte: die wichtigsten besprochenen Punkte als JSON-Array kurzer deutscher Sätze (max 6)
3. zusagen: konkrete Zusagen, die im Gespräch gemacht wurden (von wem, was), als JSON-Array (leeres Array wenn keine)
4. naechste_schritte: offene Punkte / vereinbarte nächste Schritte als JSON-Array (leeres Array wenn keine)
5. entscheidungen: konkret getroffene Entscheidungen im Gespräch (z.B. "wir machen X statt Y", eine Richtung/ein Vorgehen wurde festgelegt) als JSON-Array kurzer deutscher Sätze - NUR echte Entscheidungen, keine offenen Fragen oder bloßen Diskussionspunkte (leeres Array wenn keine)
6. datum: falls im Transkript ein konkretes Datum des Gesprächs genannt wird (z.B. "heute ist der...", ein Datum im Header, eine Terminangabe für dieses Gespräch), im Format YYYY-MM-DD - sonst null

Antworte NUR als JSON, keine Erklärung. Format:
{{"teilnehmer": [...], "kernpunkte": [...], "zusagen": [...], "naechste_schritte": [...], "entscheidungen": [...], "datum": "YYYY-MM-DD" oder null}}"""

    try:
        raw = complete_json(prompt, model=Models.SONNET, max_tokens=800).strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception:
        return None


def _resolve_datum(meeting_data: dict | None, filepath: Path) -> str:
    """Bestimmt das Ablage-Datum: bevorzugt ein im Transkript genanntes Datum,
    sonst die mtime der Original-Inbox-Datei (näher am echten Gesprächs-
    zeitpunkt als der Verarbeitungsmoment bei verzögertem Import), sonst
    'jetzt' als letzter Fallback. Behebt den Bug, dass verspätet verarbeitete
    Transkripte fälschlich das Verarbeitungsdatum statt des echten Meeting-
    Datums bekamen (Sebastian, 2026-07-18)."""
    heute = datetime.now().date()
    llm_datum = (meeting_data or {}).get("datum")
    if llm_datum:
        try:
            geparst = datetime.strptime(llm_datum, "%Y-%m-%d").date()
            if date(2020, 1, 1) <= geparst <= heute:
                return geparst.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass
    try:
        return datetime.fromtimestamp(filepath.stat().st_mtime).strftime("%Y-%m-%d")
    except OSError:
        return heute.strftime("%Y-%m-%d")


def _append_decisions_log(entscheidungen: list, quelle: str, datum: str) -> None:
    """Zentrales, vault-weites Entscheidungsprotokoll (Umsetzungsplan-Memo
    2026-07-16, Punkt B1 - "Decision Log" aus dem Everlast-AI-Company-Brain-
    Konzept). Ergänzung zu extract_meeting_structure(): jede dort erkannte
    Entscheidung landet zusätzlich hier gesammelt, damit sie nicht nur im
    einzelnen Meeting-Dokument, sondern durchsuchbar an einem Ort steht."""
    if not entscheidungen:
        return
    settings = get_settings()
    log_path = settings.agent_dir / "decisions.md"
    if not log_path.exists():
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("# Entscheidungsprotokoll\n\n", encoding="utf-8")
    with open(log_path, "a", encoding="utf-8") as f:
        for entscheidung in entscheidungen:
            f.write(f"- {datum} | {quelle} | {entscheidung}\n")


def process_file(filepath: Path) -> tuple[bool, str]:
    settings = get_settings()
    if filepath.suffix.lower() in SKIP_EXTENSIONS:
        return False, "Code-Datei übersprungen"

    content = extract_text(filepath)
    if content is None:
        return False, "Extraktion fehlgeschlagen"

    result = classify(filepath, content)
    if not result:
        return False, "API-Klassifizierung fehlgeschlagen"

    zielordner = settings.vault_path / result.get("zielordner", "Memos")
    zielordner.mkdir(parents=True, exist_ok=True)

    meeting_data = None
    if "/Meetings" in result.get("zielordner", ""):
        meeting_data = extract_meeting_structure(filepath)
    datum = _resolve_datum(meeting_data, filepath)

    if filepath.suffix.lower() not in IMAGE_EXTS | {".zip"}:
        tags = result.get("tags", [])
        tags_str = "\n".join(f"  - {t}" for t in tags)
        notiz_path = zielordner / f"{datum}-{filepath.stem}.md"

        meeting_sections = ""
        if "/Meetings" in result.get("zielordner", ""):
            if meeting_data:
                def _liste(items):
                    return "\n".join(f"- {i}" for i in items) if items else "- (keine)"
                meeting_sections = f"""
## Teilnehmer
{_liste(meeting_data.get("teilnehmer", []))}

## Kernpunkte
{_liste(meeting_data.get("kernpunkte", []))}

## Zusagen
{_liste(meeting_data.get("zusagen", []))}

## Nächste Schritte
{_liste(meeting_data.get("naechste_schritte", []))}

## Entscheidungen
{_liste(meeting_data.get("entscheidungen", []))}
"""
                _append_decisions_log(meeting_data.get("entscheidungen", []), filepath.name, datum)

        notiz_path.write_text(
            f"""---
tags:
{tags_str}
quelle: {filepath.name}
datum: {datum}
kategorie: {result.get("kategorie", "")}
---

# {filepath.stem}

## Zusammenfassung
{result.get("zusammenfassung", "")}
{meeting_sections}
## Vollständiger Inhalt
{content[:6000]}
""",
            encoding="utf-8",
        )

    safe_name = filepath.name.replace("@", "-at-")
    ziel_original = zielordner / safe_name
    ziel = ziel_original if not ziel_original.exists() else zielordner / f"{datum}-{safe_name}"
    try:
        shutil.move(str(filepath), str(ziel))
    except Exception:
        try:
            shutil.copy2(str(filepath), str(ziel))
            filepath.unlink(missing_ok=True)
        except Exception:
            pass

    log_path = settings.agent_dir / "logs" / "inbox_log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(
            f"- {datetime.now().strftime('%Y-%m-%d %H:%M')} | {filepath.name} → "
            f"{result.get('zielordner')} | {result.get('zusammenfassung', '')[:80]}\n"
        )

    return True, result.get("zielordner", "")


def run_inbox() -> dict:
    """Verarbeitet alle neuen Dateien in _inbox/. Entspricht heartbeat.py:run()."""
    settings = get_settings()
    fehler_path = settings.inbox_dir / "_fehler"
    daily_path = settings.agent_dir / "daily"
    fehler_path.mkdir(parents=True, exist_ok=True)
    daily_path.mkdir(parents=True, exist_ok=True)

    dateien = [
        f for f in settings.inbox_dir.rglob("*")
        if f.is_file()
        and not f.name.startswith(".")
        and f.suffix.lower() not in SKIP_EXTENSIONS
        and f.name not in SKIP_NAMES
        and not any(f.name.startswith(p) for p in SKIP_PREFIXES)
        and "node_modules" not in str(f)
        and "_fehler" not in str(f)
    ]

    cache = _load_cache()
    dateien = [d for d in dateien if str(d) not in cache]

    if not dateien:
        return {"processed": 0, "errors": 0, "output": "Inbox leer (alle Dateien bereits verarbeitet)."}

    processed = 0
    errors = 0
    log_lines = []
    for datei in dateien:
        try:
            ok, info = process_file(datei)
        except Exception as e:
            ok, info = False, f"Unerwarteter Fehler: {e}"
        if ok:
            cache.add(str(datei))
            _save_cache(cache)
            processed += 1
            log_lines.append(f"{datei.name} -> {info}")
        else:
            errors += 1
            log_lines.append(f"{datei.name}: FEHLER {info}")
            if info != "Code-Datei übersprungen":
                try:
                    shutil.move(str(datei), str(fehler_path / datei.name))
                except Exception:
                    pass

    daily_file = daily_path / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(daily_file, "a", encoding="utf-8") as f:
        f.write(f"\n## Inbox-Verarbeitung {datetime.now().strftime('%H:%M')}\n")
        f.write(f"- Verarbeitet: {processed}\n")
        f.write(f"- Fehler: {errors}\n")

    return {"processed": processed, "errors": errors, "output": "\n".join(log_lines)}
