import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.config import get_settings
from app.database import async_session, init_db
from app.deps import hash_password
from app.models.user import User
from app.routes import auth, dashboard, guilds, interactions
from app.services.retry import retry_loop

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await init_db()

    async with async_session() as session:
        existing = await session.scalar(select(User).where(User.email == settings.admin_email))
        if existing is None:
            session.add(
                User(
                    email=settings.admin_email,
                    password_hash=hash_password(settings.admin_password),
                )
            )
            await session.commit()
            logger.info("Seeded admin user %s", settings.admin_email)

    stop_event = asyncio.Event()
    retry_task = asyncio.create_task(retry_loop(stop_event))
    yield
    stop_event.set()
    await retry_task


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Abstrabit Discord Bot", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.app_url, "http://localhost:5173", "http://localhost:8000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(interactions.router)
    app.include_router(auth.router)
    app.include_router(guilds.router)
    app.include_router(dashboard.router)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    if STATIC_DIR.exists():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            if full_path.startswith("api/"):
                return {"detail": "Not found"}
            index = STATIC_DIR / "index.html"
            if index.exists():
                return FileResponse(index)
            return {"detail": "Frontend not built"}

    return app


app = create_app()
