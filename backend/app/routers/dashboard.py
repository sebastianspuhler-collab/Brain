"""Dashboard-Widgets: Status, Kalender, Gmail, Tasks. Migriert aus brain_server.py
(api_status wörtlich nicht vorhanden, aber /api/status; api_calendar; api_gmail; api_tasks)."""
import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import get_settings
from app.deps import get_current_user
from app.services import (
    calendar_lead_service,
    calendar_service,
    kunden_meta_service,
    linkedin_service,
    mail_service,
    rag,
    tasks_service,
)

router = APIRouter(prefix="/api", tags=["dashboard"])


class AddTaskRequest(BaseModel):
    text: str
    assignee: str = tasks_service.DEFAULT_ASSIGNEE
    due: str | None = None


class ToggleTaskRequest(BaseModel):
    text: str
    done: bool


class DeleteTaskRequest(BaseModel):
    text: str


class SetTaskAssigneeRequest(BaseModel):
    text: str
    assignee: str


class SetTaskDueRequest(BaseModel):
    text: str
    due: str | None = None


class KundenMetaRequest(BaseModel):
    archiviert: bool | None = None
    status_override: str | None = None
    notiz: str | None = None


@router.get("/status")
def status():
    """Öffentlich - zeigt keine sensiblen Daten, nur Verbindungsstatus."""
    return {
        "ok": True,
        "gmail": mail_service.is_connected(),
        "outlook": calendar_service.is_connected(),
        "date": datetime.now().strftime("%d.%m.%Y"),
        "rag_docs": rag.doc_count(),
    }


@router.get("/calendar")
def calendar(user: str = Depends(get_current_user)):
    return calendar_service.get_calendar_events()


@router.get("/gmail")
def gmail(user: str = Depends(get_current_user)):
    return mail_service.get_gmail_summary()


@router.get("/tasks")
def tasks(user: str = Depends(get_current_user)):
    return tasks_service.get_tasks()


@router.post("/tasks")
def add_task(body: AddTaskRequest, user: str = Depends(get_current_user)):
    return tasks_service.add_task(body.text, body.assignee, body.due)


@router.post("/tasks/toggle")
def toggle_task(body: ToggleTaskRequest, user: str = Depends(get_current_user)):
    return tasks_service.toggle_task(body.text, body.done)


@router.post("/tasks/delete")
def delete_task(body: DeleteTaskRequest, user: str = Depends(get_current_user)):
    return tasks_service.delete_task(body.text)


@router.post("/tasks/assignee")
def set_task_assignee(body: SetTaskAssigneeRequest, user: str = Depends(get_current_user)):
    return tasks_service.set_task_assignee(body.text, body.assignee)


@router.post("/tasks/due")
def set_task_due(body: SetTaskDueRequest, user: str = Depends(get_current_user)):
    return tasks_service.set_task_due(body.text, body.due)


# ── Management-Dashboard-Erweiterung (Umsetzungsplan-Memo 2026-07-16, Punkt B3;
# Status-Pipeline + Leads-Integration 2026-07-19) ──────────────────────────
# Bewusst NUR auf Basis tatsächlich vorhandener Daten (Ordnerinhalte, Meeting-
# Extraktion, Kalender) - keine "offene Rechnungen"-Kachel und keine erfundene
# Bewertung, wo echte Daten fehlen.
_STATUS_RANK = {
    "neuer_kontakt": 0, "erstgespraech": 1, "angebotsphase": 2,
    "auftrag": 3, "fulfillment": 4, "abgeschlossen": 5,
}

# Die Vollständigkeits-Ansicht war der eigene Menüpunkt "Spaces", ist auf
# Sebastians Wunsch (2026-07-18) Teil der Kunden-Karte im Dashboard - dieselben
# vier Standard-Unterordner wie classify.classify() sie für neue Kunden anlegt.
_STANDARD_ORDNER = ("Vertraege", "Angebote", "Meetings", "Dokumente")

# Massenlisten-Quelltypen (Excel/CSV-Kaltakquise-Importe) vs. echte Einzel-
# Interessenten (Sebastian, 2026-07-19: "Leads/" mischt beides, nur echte
# Einzel-Interessenten gehören ins Dashboard). Sowohl Massenlisten als auch
# echte Leads durchlaufen dieselbe classify()-Pipeline und tragen beide
# "kategorie: Lead" - der zuverlässige Unterschied ist die Quelldatei-Endung
# im Frontmatter-Feld "quelle:" (Tabelle vs. Dokument/Kalender), nicht der
# Dateiname selbst. Verifiziert gegen den kompletten Leads/-Bestand: 31 von 47
# Dateien sind xlsx/csv-Massenlisten.
_LEADS_MASSENLISTE_EXTS = (".xlsx", ".csv")


def _hat_dateien(ordner) -> bool:
    return ordner.exists() and any(f.is_file() for f in ordner.glob("*"))


def _vollstaendigkeit(kunde_path) -> int:
    vorhanden = sum(1 for sub in _STANDARD_ORDNER if _hat_dateien(kunde_path / sub))
    return round(vorhanden / len(_STANDARD_ORDNER) * 100)


def _status_automatisch_kunde(kunde_path) -> str:
    """Deterministisch aus real vorhandenen Ordnerinhalten - "fulfillment" und
    "abgeschlossen" lassen sich daraus NICHT verlässlich ableiten (ein
    Vertrags-Ordner sagt nichts über den operativen Stand aus), deshalb nur
    über den manuellen status_override erreichbar."""
    if _hat_dateien(kunde_path / "Vertraege"):
        return "auftrag"
    if _hat_dateien(kunde_path / "Angebote"):
        return "angebotsphase"
    if _hat_dateien(kunde_path / "Meetings"):
        return "erstgespraech"
    return "neuer_kontakt"


def _letzte_aktivitaet(ordner) -> str | None:
    dates = [
        m.group(1) for f in ordner.rglob("*.md")
        if (m := re.match(r"^(\d{4}-\d{2}-\d{2})", f.name))
    ]
    return max(dates) if dates else None


def _aktueller_stand(meetings_dir) -> str:
    """Erster Punkt aus "Nächste Schritte" der jüngsten Meeting-Datei - kein
    neuer LLM-Call, reine Textextraktion aus bereits vorhandenem Inhalt
    (extract_meeting_structure() schreibt diesen Abschnitt in classify.py)."""
    if not meetings_dir.exists():
        return ""
    dateien = sorted(meetings_dir.glob("*.md"), reverse=True)
    if not dateien:
        return ""
    text = dateien[0].read_text(encoding="utf-8")
    m = re.search(r"## Nächste Schritte\n(.*?)(?:\n##|\Z)", text, re.S)
    if not m:
        return ""
    zeilen = [z.lstrip("- ").strip() for z in m.group(1).strip().splitlines() if z.strip()]
    zeilen = [z for z in zeilen if z and z != "(keine)"]
    return zeilen[0] if zeilen else ""


def _naechster_termin(name: str, termine: list[dict]) -> dict | None:
    """Sucht den frühesten kommenden Kalendertermin, dessen Titel zum Namen
    passt - wiederverwendet dasselbe erprobte Substring-Matching wie
    calendar_lead_service._is_known(), statt neu zu erfinden."""
    needle = calendar_lead_service.normalize_name(name)
    if not needle:
        return None
    treffer = [
        t for t in termine
        if (h := calendar_lead_service.normalize_name(t.get("title", "")))
        and (h in needle or needle in h)
    ]
    if not treffer:
        return None
    treffer.sort(key=lambda t: t["start"])
    return {"titel": treffer[0]["title"], "start": treffer[0]["start"]}


def _eintrag(
    name: str, status_automatisch: str, letzte_aktivitaet: str | None,
    vollstaendigkeit: int | None, aktueller_stand: str, termine: list[dict],
    tasks: list[dict], typ: str, zeige_archivierte: bool,
) -> dict | None:
    meta = kunden_meta_service.get_meta(name)
    if meta.get("archiviert") and not zeige_archivierte:
        return None
    tage_seit_aktivitaet = None
    if letzte_aktivitaet:
        try:
            tage_seit_aktivitaet = (
                datetime.now().date() - datetime.strptime(letzte_aktivitaet, "%Y-%m-%d").date()
            ).days
        except ValueError:
            pass
    status_override = meta.get("status_override")
    return {
        "kunde": name,
        "typ": typ,
        "letztes_meeting": letzte_aktivitaet,
        "tage_seit_meeting": tage_seit_aktivitaet,
        "status": status_override or status_automatisch,
        "status_automatisch": status_automatisch,
        "offene_aufgaben": sum(
            1 for t in tasks if not t.get("done") and name.lower() in t["text"].lower()
        ),
        "vollstaendigkeit": vollstaendigkeit,
        "aktueller_stand": aktueller_stand,
        "naechster_termin": _naechster_termin(name, termine),
        "archiviert": bool(meta.get("archiviert")),
        "notiz": meta.get("notiz", ""),
    }


def _ist_einzel_lead(md_path) -> bool:
    if md_path.stat().st_size == 0:
        return False
    m = re.search(r"^quelle:\s*(.+)$", md_path.read_text(encoding="utf-8"), re.M)
    if not m:
        return False
    return Path(m.group(1).strip()).suffix.lower() not in _LEADS_MASSENLISTE_EXTS


@router.get("/dashboard/kunden-status")
def kunden_status(zeige_archivierte: bool = False, user: str = Depends(get_current_user)):
    settings = get_settings()
    tasks = tasks_service.get_tasks()
    termine = calendar_service.get_calendar_events()

    result = []
    kunden_dir = settings.vault_path / "Kunden"
    if kunden_dir.exists():
        for kunde_path in sorted(kunden_dir.iterdir()):
            # "." / "[" / "_": versteckte bzw. Platzhalter-/Vorlagenordner
            # (z.B. "[NeuerKunde]", "_Vorlage") ausschließen, keine echten Kunden
            if not kunde_path.is_dir() or kunde_path.name.startswith((".", "[", "_")):
                continue
            eintrag = _eintrag(
                kunde_path.name,
                _status_automatisch_kunde(kunde_path),
                _letzte_aktivitaet(kunde_path),
                _vollstaendigkeit(kunde_path),
                _aktueller_stand(kunde_path / "Meetings"),
                termine, tasks, "kunde", zeige_archivierte,
            )
            if eintrag:
                result.append(eintrag)

    leads_dir = settings.vault_path / "Leads"
    if leads_dir.exists():
        for md_path in sorted(leads_dir.glob("*.md")):
            if not _ist_einzel_lead(md_path):
                continue
            name = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", md_path.stem)
            frontmatter_datum = None
            m = re.search(r"^datum:\s*(\d{4}-\d{2}-\d{2})", md_path.read_text(encoding="utf-8"), re.M)
            if m:
                frontmatter_datum = m.group(1)
            # Reiner Kalender-Stub (nur Termin/Teilnehmer, siehe
            # calendar_lead_service._write_lead_stub) vs. echte Notiz mit
            # Transkript-/Gesprächsinhalt - Größenschwelle statt Raten, der
            # Stub-Text selbst ist konstant kurz (~500 Zeichen).
            status = "erstgespraech" if md_path.stat().st_size > 800 else "neuer_kontakt"
            eintrag = _eintrag(
                name, status, frontmatter_datum, None, "",
                termine, tasks, "lead", zeige_archivierte,
            )
            if eintrag:
                result.append(eintrag)

    result.sort(key=lambda k: (_STATUS_RANK.get(k["status"], 9), k["kunde"]))
    return {"kunden": result}


@router.post("/dashboard/kunden/{kunde}/meta")
def set_kunden_meta(kunde: str, body: KundenMetaRequest, user: str = Depends(get_current_user)):
    return kunden_meta_service.upsert_meta(
        kunde,
        archiviert=body.archiviert,
        status_override=body.status_override,
        notiz=body.notiz,
    )


@router.get("/dashboard/linkedin-status")
def linkedin_status(user: str = Depends(get_current_user)):
    posts = linkedin_service.get_posts().get("posts", [])
    ideen = linkedin_service.get_ideas().get("ideen", [])

    gepusht = [p for p in posts if p.get("pushed")]
    geplant = sorted(
        (p for p in posts if not p.get("pushed") and p.get("termin")),
        key=lambda p: p["termin"],
    )
    naechster = geplant[0] if geplant else None

    return {
        "geplante_posts": len(geplant),
        "gepushte_posts": len(gepusht),
        "offene_ideen": len(ideen),
        "naechster_post": (
            {"termin": naechster["termin"], "idee": naechster["idee"]} if naechster else None
        ),
    }
