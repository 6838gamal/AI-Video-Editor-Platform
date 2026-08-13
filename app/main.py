from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.database import check_database, init_db
from app.modules.ai.routes import router as ai_router
from app.modules.auth.routes import router as auth_router
from app.modules.editor.routes import router as editor_router
from app.modules.processing.routes import router as processing_router
from app.modules.system.routes import router as system_router
from app.modules.system.services import SystemService
from app.modules.users.routes import router as users_router
from app.modules.videos.routes import router as videos_router
from app.modules.youtube.routes import router as youtube_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("video_editor")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

static_dir = BASE_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse({"error": "Something went wrong. Please try again."}, status_code=500)


@app.get("/health")
async def health():
    db_ok = check_database()
    return JSONResponse(
        {"status": "ok" if db_ok else "degraded", "database": "connected" if db_ok else "unavailable"},
        status_code=200,
    )


# API routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(videos_router)
app.include_router(youtube_router)
app.include_router(editor_router)
app.include_router(processing_router)
app.include_router(system_router)


# ---- Web pages ----

def _degraded(request: Request) -> bool:
    return not check_database()


@app.get("/", response_class=HTMLResponse)
async def page_dashboard(request: Request):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "app_name": settings.app_name, "degraded": _degraded(request), "page": "dashboard"},
    )


@app.get("/login", response_class=HTMLResponse)
async def page_login(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "app_name": settings.app_name, "degraded": _degraded(request), "page": "login"},
    )


@app.get("/register", response_class=HTMLResponse)
async def page_register(request: Request):
    return templates.TemplateResponse(
        "register.html",
        {"request": request, "app_name": settings.app_name, "degraded": _degraded(request), "page": "register"},
    )


@app.get("/editor/{video_id}", response_class=HTMLResponse)
async def page_editor(request: Request, video_id: str):
    return templates.TemplateResponse(
        "editor.html",
        {"request": request, "app_name": settings.app_name, "degraded": _degraded(request), "page": "editor", "video_id": video_id},
    )


@app.get("/result/{job_id}", response_class=HTMLResponse)
async def page_result(request: Request, job_id: str):
    return templates.TemplateResponse(
        "result.html",
        {"request": request, "app_name": settings.app_name, "degraded": _degraded(request), "page": "result", "job_id": job_id},
    )
