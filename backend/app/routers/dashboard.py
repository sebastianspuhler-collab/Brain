"""Dashboard-Widgets: Status, Kalender, Gmail, Tasks. Migriert aus brain_server.py
(api_status wörtlich nicht vorhanden, aber /api/status; api_calendar; api_gmail; api_tasks)."""
import re
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import get_settings
from app.deps import get_current_user
from app.services import calendar_service, linkedin_service, mail_service, rag, tasks_service

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


# ── Management-Dashboard-Erweiterung (Umsetzungsplan-Memo 2026-07-16, Punkt B3) ──
# Ergänzung zu den bestehenden Widgets oben, keins davon wird verändert. Bewusst
# NUR auf Basis tatsächlich vorhandener Daten (Meeting-Termine, Aufgabentexte,
# Buffer-Planungsstatus) - keine "offene Rechnungen"-Kachel, weil im Vault
# nirgends ein Bezahlt/Offen-Status zu Rechnungen gepflegt wird und das sonst
# erfundene Zahlen wären.
_AMPEL_RANK = {"rot": 0, "gelb": 1, "grau": 2, "gruen": 3}


@router.get("/dashboard/kunden-status")
def kunden_status(user: str = Depends(get_current_user)):
    settings = get_settings()
    kunden_dir = settings.vault_path / "Kunden"
    if not kunden_dir.exists():
        return {"kunden": []}

    tasks = tasks_service.get_tasks()
    today = datetime.now().date()
    result = []
    for kunde_path in sorted(kunden_dir.iterdir()):
        # "." / "[" / "_": versteckte bzw. Platzhalter-/Vorlagenordner (z.B.
        # "[NeuerKunde]", "_Vorlage") ausschließen, keine echten Kunden
        if not kunde_path.is_dir() or kunde_path.name.startswith((".", "[", "_")):
            continue
        name = kunde_path.name
        # Nicht nur Meetings/ - sonst zeigt die Ampel "grau" (keine Daten) für
        # Kunden, bei denen zwar laufend Dokumente/Verträge/Korrespondenz
        # reinkommen, aber zufällig kein Meeting protokolliert wurde. Letzte
        # Aktivität = jüngstes datierten Datei irgendwo im Kundenordner.
        dates = []
        for f in kunde_path.rglob("*.md"):
            m = re.match(r"^(\d{4}-\d{2}-\d{2})", f.name)
            if m:
                dates.append(m.group(1))
        letztes_meeting = max(dates) if dates else None

        tage_seit_meeting = None
        ampel = "grau"
        if letztes_meeting:
            try:
                d = datetime.strptime(letztes_meeting, "%Y-%m-%d").date()
                tage_seit_meeting = (today - d).days
                if tage_seit_meeting <= 30:
                    ampel = "gruen"
                elif tage_seit_meeting <= 90:
                    ampel = "gelb"
                else:
                    ampel = "rot"
            except ValueError:
                pass

        offene_aufgaben = sum(
            1 for t in tasks if not t.get("done") and name.lower() in t["text"].lower()
        )

        result.append({
            "kunde": name,
            "letztes_meeting": letztes_meeting,
            "tage_seit_meeting": tage_seit_meeting,
            "ampel": ampel,
            "offene_aufgaben": offene_aufgaben,
        })

    result.sort(key=lambda k: (_AMPEL_RANK.get(k["ampel"], 9), k["kunde"]))
    return {"kunden": result}


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
