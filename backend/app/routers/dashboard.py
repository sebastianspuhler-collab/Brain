"""Dashboard-Widgets: Status, Kalender, Gmail, Tasks. Migriert aus brain_server.py
(api_status wörtlich nicht vorhanden, aber /api/status; api_calendar; api_gmail; api_tasks)."""
from datetime import datetime

from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.services import calendar_service, mail_service, rag, tasks_service

router = APIRouter(prefix="/api", tags=["dashboard"])


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
