from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
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


# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("video_editor")


# ---------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        logger.info("Database initialization completed.")
    except Exception as exc:
        # لا نوقف التطبيق إذا كانت قاعدة البيانات غير متاحة
        logger.warning("Database initialization failed: %s", exc)

    yield


# ---------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)

static_dir = BASE_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)

app.mount(
    "/static",
    StaticFiles(directory=str(static_dir)),
    name="static",
)


# ---------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------

@app.exception_handler(Exception)
async def unhandled_exception(
    request: Request,
    exc: Exception,
):
    logger.exception(
        "Unhandled error on %s %s: %s",
        request.method,
        request.url.path,
        exc,
    )

    return JSONResponse(
        {
            "error": "Something went wrong. Please try again."
        },
        status_code=500,
    )


# ---------------------------------------------------------
# Health check
# ---------------------------------------------------------

@app.get("/health")
async def health():
    try:
        db_ok = check_database()
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        db_ok = False

    return JSONResponse(
        {
            "status": "ok" if db_ok else "degraded",
            "database": (
                "connected"
                if db_ok
                else "unavailable"
            ),
        },
        status_code=200,
    )


# ---------------------------------------------------------
# API routers
# ---------------------------------------------------------

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(videos_router)
app.include_router(youtube_router)
app.include_router(editor_router)
app.include_router(processing_router)
app.include_router(system_router)
app.include_router(ai_router)


# ---------------------------------------------------------
# Web helpers
# ---------------------------------------------------------

def _degraded(request: Request) -> bool:
    try:
        return not check_database()
    except Exception as exc:
        logger.warning(
            "Could not check database status: %s",
            exc,
        )
        return True


# ---------------------------------------------------------
# Root
# ---------------------------------------------------------
# عند فتح الموقع مباشرة:
#
# /
#
# يتم تحويل المستخدم إلى:
#
# /login
#
# ---------------------------------------------------------

@app.get("/")
async def page_root():
    return RedirectResponse(
        url="/login",
        status_code=302,
    )


# ---------------------------------------------------------
# Login page
# ---------------------------------------------------------

@app.get(
    "/login",
    response_class=HTMLResponse,
)
async def page_login(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "degraded": _degraded(request),
            "page": "login",
        },
    )


# ---------------------------------------------------------
# Register page
# ---------------------------------------------------------

@app.get(
    "/register",
    response_class=HTMLResponse,
)
async def page_register(request: Request):
    return templates.TemplateResponse(
        "register.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "degraded": _degraded(request),
            "page": "register",
        },
    )


# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------

@app.get(
    "/dashboard",
    response_class=HTMLResponse,
)
async def page_dashboard(request: Request):
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "degraded": _degraded(request),
            "page": "dashboard",
        },
    )


# ---------------------------------------------------------
# Video editor
# ---------------------------------------------------------

@app.get(
    "/editor/{video_id}",
    response_class=HTMLResponse,
)
async def page_editor(
    request: Request,
    video_id: str,
):
    return templates.TemplateResponse(
        "editor.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "degraded": _degraded(request),
            "page": "editor",
            "video_id": video_id,
        },
    )


# ---------------------------------------------------------
# Processing result
# ---------------------------------------------------------

@app.get(
    "/result/{job_id}",
    response_class=HTMLResponse,
)
async def page_result(
    request: Request,
    job_id: str,
):
    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "degraded": _degraded(request),
            "page": "result",
            "job_id": job_id,
        },
    )
