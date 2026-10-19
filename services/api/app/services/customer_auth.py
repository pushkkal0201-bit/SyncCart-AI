from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.core.exceptions import (
    InvalidSessionToken,
    SessionTokenExpired,
    SessionTokenUnavailable,
)
from app.models.shopping_session import ShoppingSession
from app.models.mixins import utcnow


class CustomerAuthService:
    def __init__(self) -> None:
        self.settings = get_settings()

    @staticmethod
    def hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    def issue_token(self) -> tuple[str, str, datetime]:
        raw_token = secrets.token_urlsafe(32)
        token_hash = self.hash_token(raw_token)
        expires_at = utcnow() + timedelta(minutes=self.settings.customer_session_token_ttl_minutes)
        return raw_token, token_hash, expires_at

    def verify(self, shopping_session: ShoppingSession, raw_token: str | None) -> None:
        if not shopping_session.customer_token_hash or shopping_session.customer_token_expires_at is None:
            raise SessionTokenUnavailable(
                "This session was created before customer token support was enabled. Start a new session."
            )
        if not raw_token:
            raise InvalidSessionToken("Customer session token is required")

        incoming_hash = self.hash_token(raw_token)
        if not hmac.compare_digest(incoming_hash, shopping_session.customer_token_hash):
            raise InvalidSessionToken("Customer session token is invalid")

        expires_at = shopping_session.customer_token_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if utcnow() >= expires_at:
            raise SessionTokenExpired("Customer session token has expired")
