from __future__ import annotations

from fastapi import Request


def request_id(request: Request) -> str:
    return str(request.state.request_id)
