from __future__ import annotations

import hmac

from app.core.config import get_settings
from app.core.exceptions import DomainError


class MonitoringAccessDenied(DomainError):
    code = "MONITORING_ACCESS_DENIED"
    status_code = 401


class MonitoringAuthService:
    """Local AI/system-operations access boundary.

    Phase 4D deliberately separates system-operator authority from retailer authority.
    Production should replace this local API key with workforce identity, MFA, and RBAC.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    def verify(self, supplied_key: str | None) -> None:
        configured = self.settings.monitoring_api_key
        if not configured:
            raise MonitoringAccessDenied("Monitoring access is not configured")
        if supplied_key is None or not hmac.compare_digest(supplied_key, configured):
            raise MonitoringAccessDenied("Invalid monitoring access key")
