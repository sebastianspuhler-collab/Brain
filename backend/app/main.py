import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.background.jobs import (
    attachment_backfill_loop,
    calendar_lead_loop,
    email_indexer_loop,
    git_sync_loop,
    inbox_watcher_loop,
    load_rag_blocking,
)
from app.config import get_settings
from app.routers import auth, chat, dashboard, files, inbox, linkedin, onboarding, youtube
from app.routers.auth import limiter
from app.services.claude_cli import ensure_mcp_approval

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_mcp_approval()
    await asyncio.to_thread(load_rag_blocking)
    tasks = [
        asyncio.create_task(inbox_watcher_loop()),
        asyncio.create_task(email_indexer_loop()),
        asyncio.create_task(git_sync_loop()),
        asyncio.create_task(calendar_lead_loop()),
        asyncio.create_task(attachment_backfill_loop()),
    ]
    yield
    for task in tasks:
        task.cancel()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Prozessia Brain", lifespan=lifespan)

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.cors_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(chat.router)
    app.include_router(dashboard.router)
    app.include_router(files.router)
    app.include_router(linkedin.router)
    app.include_router(youtube.router)
    app.include_router(inbox.router)
    app.include_router(onboarding.router)

    return app


app = create_app()
