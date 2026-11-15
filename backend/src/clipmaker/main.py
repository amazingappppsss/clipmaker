"""FastAPI application factory.

Run locally:  uvicorn clipmaker.main:app --reload
The API never processes video synchronously; heavy work goes to Celery workers.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from clipmaker import __version__
from clipmaker.api import account, dev, health, local_storage, plans, projects, waitlist
from clipmaker.core.config import AppEnv, StorageBackend, get_settings
from clipmaker.core.errors import AppError
from clipmaker.core.logging import configure_logging
from clipmaker.storage.local import request_base_url

logger = logging.getLogger("clipmaker.api")


def public_base_url(request: Request) -> str:
    """The address the browser used to reach us, honouring the platform's proxy headers."""
    proto = request.headers.get("x-forwarded-proto", request.url.scheme).split(",")[0].strip()
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "localhost"))
    return f"{proto}://{host.split(',')[0].strip()}"


def create_app() -> FastAPI:
    """Build the application with routers, middleware and error handlers."""
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(
        title="Clip2Easy API",
        version=__version__,
        # Closed unless explicitly opened. The previous rule — open unless APP_ENV is
        # exactly "production" — left /docs, /redoc and /openapi.json serving the whole API
        # surface publicly the moment that one variable was unset or spelled differently.
        docs_url="/docs" if settings.expose_api_docs else None,
        redoc_url="/redoc" if settings.expose_api_docs else None,
        openapi_url="/openapi.json" if settings.expose_api_docs else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,  # bearer tokens, not cookies
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def request_logging(request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request_base_url.set(public_base_url(request))
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        # Hardening. The API returns JSON to our own origin only, so it has no reason to be
        # framed, sniffed, or to leak the path it was called from.
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
            },
        )
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content={"code": exc.code, "message": exc.message}
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(p) for p in first.get("loc", [])[1:]) or "request"
        return JSONResponse(
            status_code=422,
            content={
                "code": "invalid_request",
                "message": f"{field}: {first.get('msg', 'invalid')}",
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error", extra={"path": request.url.path})
        return JSONResponse(
            status_code=500, content={"code": "internal_error", "message": "Something went wrong."}
        )

    app.include_router(health.router)
    app.include_router(projects.router)
    app.include_router(projects.shared_router)
    app.include_router(account.router)
    app.include_router(plans.router)
    app.include_router(waitlist.router)
    if settings.storage_backend == StorageBackend.LOCAL:
        app.include_router(local_storage.router)
    if settings.enable_dev_auth and settings.app_env != AppEnv.PRODUCTION:
        app.include_router(dev.router)
    return app


app = create_app()
