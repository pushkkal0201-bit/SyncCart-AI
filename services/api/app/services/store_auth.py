from __future__ import annotations

import hmac

from app.core.config import get_settings
from app.core.exceptions import DomainError


class StoreAccessDenied(DomainError):
    code = "STORE_ACCESS_DENIED"
    status_code = 401


class StoreAuthService:
    """Local store-operations access boundary.

    Phase 4C uses a local API key so the retailer app is not anonymously exposed.
    Production should replace this with employee identity + RBAC.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    def verify(self, supplied_key: str | None) -> None:
        configured = self.settings.store_ops_api_key
        if not configured:
            raise StoreAccessDenied("Store operations access is not configured")
        if supplied_key is None or not hmac.compare_digest(supplied_key, configured):
            raise StoreAccessDenied("Invalid store operations access key")
