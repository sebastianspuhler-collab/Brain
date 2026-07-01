"""Dashboard-Widgets: Status, Kalender, Gmail, Tasks. Migriert aus brain_server.py
(api_status wörtlich nicht vorhanden, aber /api/status; api_calendar; api_gmail; api_tasks)."""
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.deps import get_current_user
from app.services import calendar_service, mail_service, rag, tasks_service

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
