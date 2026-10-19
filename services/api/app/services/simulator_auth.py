from __future__ import annotations

import hmac

from app.core.config import get_settings
from app.core.exceptions import InvalidSimulatorKey, SimulatorDisabled


class SimulatorAuthService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def verify(self, supplied_key: str | None) -> None:
        if not self.settings.enable_simulator:
            raise SimulatorDisabled(
                "Simulator endpoints are disabled. Set ENABLE_SIMULATOR=true in the local environment."
            )
        expected = self.settings.simulator_api_key.strip()
        if not expected:
            raise SimulatorDisabled(
                "Simulator API key is not configured. Set SIMULATOR_API_KEY in .env."
            )
        if not supplied_key or not hmac.compare_digest(supplied_key, expected):
            raise InvalidSimulatorKey("Simulator API key is invalid")
