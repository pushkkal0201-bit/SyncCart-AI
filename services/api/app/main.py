from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.health import router as health_router
from app.api.router import api_router
from app.api.ws.customer import router as customer_ws_router
from app.api.ws.store import router as store_ws_router
from app.api.ws.monitoring import router as monitoring_ws_router
from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.schemas.common import Envelope, ErrorBody
from app.services.reconciliation_worker import run_reconciliation_worker

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("synccart.api")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    stop_event = asyncio.Event()
    worker_task: asyncio.Task[None] | None = None
    if settings.enable_reconciliation_worker:
        worker_task = asyncio.create_task(run_reconciliation_worker(stop_event))
    try:
        yield
    finally:
        if worker_task is not None:
            stop_event.set()
            await worker_task


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "SyncCart AI: three-app platform plus retail CCTV/Phone camera Vision ingestion, edge worker "
        "contracts, cart reconciliation, operational telemetry, and edge-first runtime integration."
    ),
    lifespan=lifespan,
)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        settings.request_id_header,
        settings.idempotency_header,
        settings.customer_session_token_header,
        settings.simulator_api_key_header,
        settings.store_ops_api_key_header,
        settings.monitoring_api_key_header,
        settings.vision_api_key_header,
    ],
)
if settings.app_env == "production":
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

app.include_router(health_router)
app.include_router(api_router, prefix=settings.api_v1_prefix)
app.include_router(customer_ws_router, prefix="/ws")
app.include_router(store_ws_router, prefix="/ws")
app.include_router(monitoring_ws_router, prefix="/ws")


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(
        "domain_error",
        extra={"request_id": request_id, "error_code": exc.code, "details": exc.details},
    )
    body = Envelope[object](
        data=None,
        meta={"request_id": request_id},
        error=ErrorBody(code=exc.code, message=exc.message, details=exc.details),
    )
    return JSONResponse(status_code=exc.status_code, content=body.model_dump(mode="json"))


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    body = Envelope[object](
        data=None,
        meta={"request_id": request_id},
        error=ErrorBody(
            code="VALIDATION_ERROR",
            message="The request payload or parameters are invalid.",
            details={"errors": exc.errors()},
        ),
    )
    return JSONResponse(status_code=422, content=body.model_dump(mode="json"))


@app.get("/", include_in_schema=False)
async def root(request: Request) -> dict[str, str]:
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "request_id": request.state.request_id,
    }
