from __future__ import annotations

import time
from uuid import UUID, uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.config import get_settings


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()
        incoming = request.headers.get(settings.request_id_header)
        try:
            request_id = str(UUID(incoming)) if incoming else str(uuid4())
        except ValueError:
            request_id = str(uuid4())

        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers[settings.request_id_header] = request_id
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response
