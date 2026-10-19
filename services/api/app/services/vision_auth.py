from __future__ import annotations

import hmac

from app.core.config import get_settings
from app.core.exceptions import DomainError


class VisionAccessDenied(DomainError):
    code = "VISION_ACCESS_DENIED"
    status_code = 401


class VisionAuthService:
    """Authenticates the dedicated edge-Vision worker.

    The deployment uses a separate Vision API key so the camera worker never needs the
    customer, retailer, or monitoring credentials. Production should replace this
    with device identity, signed service credentials, and store-scoped authorization.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    def verify(self, supplied_key: str | None) -> None:
        configured = self.settings.vision_api_key.strip()
        if not configured:
            raise VisionAccessDenied("Vision worker access is not configured")
        if supplied_key is None or not hmac.compare_digest(supplied_key, configured):
            raise VisionAccessDenied("Invalid Vision worker access key")
