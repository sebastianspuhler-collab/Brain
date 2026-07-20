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
    kunden_status_service,
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
    overrides: dict[str, str] | None = None


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
# Status-Pipeline + Leads-Integration 2026-07-19; LLM-Status-Synthese 2026-07-20)
# Der Status selbst kommt jetzt aus kunden_status_service (liest E-Mails,
# Meeting-Extrakte und Termine, nicht nur Ordner-Anwesenheit) - siehe dort für
# die Begründung. _STATUS_RANK bleibt hier nur fürs Sortieren der Liste.
_STATUS_RANK = kunden_status_service.STATUS_RANK

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


def _letzte_aktivitaet(ordner) -> str | None:
    dates = [
        m.group(1) for f in ordner.rglob("*.md")
        if (m := re.match(r"^(\d{4}-\d{2}-\d{2})", f.name))
    ]
    return max(dates) if dates else None


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
    name: str, status_info: dict, letzte_aktivitaet: str | None,
    vollstaendigkeit: int | None, naechster_termin: dict | None,
    tasks: list[dict], typ: str, zeige_archivierte: bool, zeige_irrelevante: bool, meta: dict,
) -> dict | None:
    if meta.get("archiviert") and not zeige_archivierte:
        return None
    if not status_info.get("ist_relevant", True) and not zeige_irrelevante:
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
    # Nur die interpretativen Felder sind übersteuerbar (Sebastian, 2026-07-20:
    # Fakten wie Vollständigkeit/Termin/Aufgaben bleiben rein automatisch, ein
    # Override dort könnte der echten Dateilage widersprechen).
    overrides = meta.get("overrides") or {}
    anzeige_name = overrides.get("anzeige_name") or status_info.get("anzeige_name") or name
    aktueller_stand = overrides.get("aktueller_stand") or status_info.get("aktueller_stand") or ""
    return {
        "kunde": name,
        "anzeige_name": anzeige_name,
        "typ": typ,
        "letztes_meeting": letzte_aktivitaet,
        "tage_seit_meeting": tage_seit_aktivitaet,
        "status": status_override or status_info["status"],
        "status_automatisch": status_info["status"],
        "sicherheit": status_info["sicherheit"],
        "begruendung": status_info["begruendung"],
        "quellen": status_info["quellen"],
        "warnsignal": status_info["warnsignal"],
        "ist_relevant": status_info.get("ist_relevant", True),
        "relevanz_begruendung": status_info.get("relevanz_begruendung") or "",
        "offene_aufgaben": sum(
            1 for t in tasks if not t.get("done") and name.lower() in t["text"].lower()
        ),
        "vollstaendigkeit": vollstaendigkeit,
        "aktueller_stand": aktueller_stand,
        "naechster_termin": naechster_termin,
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
def kunden_status(
    zeige_archivierte: bool = False, zeige_irrelevante: bool = False,
    user: str = Depends(get_current_user),
):
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
            meta = kunden_meta_service.get_meta(kunde_path.name)
            naechster_termin = _naechster_termin(kunde_path.name, termine)
            status_info = kunden_status_service.get_status(
                kunde_path.name, kunde_path,
                notiz=meta.get("notiz", ""), naechster_termin=naechster_termin,
            )
            eintrag = _eintrag(
                kunde_path.name, status_info,
                _letzte_aktivitaet(kunde_path),
                _vollstaendigkeit(kunde_path),
                naechster_termin, tasks, "kunde", zeige_archivierte, zeige_irrelevante, meta,
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
            meta = kunden_meta_service.get_meta(name)
            naechster_termin = _naechster_termin(name, termine)
            # Leads laufen seit 2026-07-20 durch dieselbe LLM-Synthese wie
            # Kunden (kunden_status_service unterstützt seitdem eine einzelne
            # Datei statt eines Kundenordners) - vorher gab es hier nur eine
            # Byte-Größen-Heuristik ohne "aktueller_stand" und ohne
            # Relevanz-Prüfung.
            status_info = kunden_status_service.get_status(
                name, md_path, notiz=meta.get("notiz", ""), naechster_termin=naechster_termin,
            )
            eintrag = _eintrag(
                name, status_info, frontmatter_datum, None,
                naechster_termin, tasks, "lead", zeige_archivierte, zeige_irrelevante, meta,
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
        overrides=body.overrides,
    )


@router.post("/dashboard/kunden/{kunde}/neu-bewerten")
def kunden_neu_bewerten(kunde: str, user: str = Depends(get_current_user)):
    """Erzwingt eine sofortige Neubewertung statt auf die nächste Dateiänderung
    zu warten - Sebastians Steuerungshebel z.B. nach einem Telefonat, das (noch)
    nicht als Dokument im Vault liegt, oder nach einer neuen Notiz. Funktioniert
    seit der Lead-LLM-Synthese (2026-07-20) für Kunden UND Leads."""
    settings = get_settings()
    kunde_path = settings.vault_path / "Kunden" / kunde
    if not kunde_path.exists():
        leads_dir = settings.vault_path / "Leads"
        kunde_path = next(
            (
                p for p in leads_dir.glob("*.md")
                if re.sub(r"^\d{4}-\d{2}-\d{2}-", "", p.stem) == kunde
            ),
            None,
        ) if leads_dir.exists() else None
    if not kunde_path or not kunde_path.exists():
        return {"error": "Kunde/Lead nicht gefunden"}
    meta = kunden_meta_service.get_meta(kunde)
    naechster_termin = _naechster_termin(kunde, calendar_service.get_calendar_events())
    return kunden_status_service.get_status(
        kunde, kunde_path, notiz=meta.get("notiz", ""),
        naechster_termin=naechster_termin, force=True,
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
