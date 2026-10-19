from __future__ import annotations


class DomainError(Exception):
    code = "DOMAIN_ERROR"
    status_code = 400

    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ProductNotFound(DomainError):
    code = "PRODUCT_NOT_FOUND"
    status_code = 404


class ProductConflict(DomainError):
    code = "PRODUCT_CONFLICT"
    status_code = 409


class SessionNotFound(DomainError):
    code = "SESSION_NOT_FOUND"
    status_code = 404


class InvalidSessionToken(DomainError):
    code = "INVALID_SESSION_TOKEN"
    status_code = 401


class SessionTokenExpired(DomainError):
    code = "SESSION_TOKEN_EXPIRED"
    status_code = 401


class SessionTokenUnavailable(DomainError):
    code = "SESSION_TOKEN_UNAVAILABLE"
    status_code = 401


class InvalidIdempotencyKey(DomainError):
    code = "INVALID_IDEMPOTENCY_KEY"
    status_code = 400


class IdempotencyConflict(DomainError):
    code = "IDEMPOTENCY_CONFLICT"
    status_code = 409


class CartItemNotFound(DomainError):
    code = "CART_ITEM_NOT_FOUND"
    status_code = 404


class CartQuantityConflict(DomainError):
    code = "CART_QUANTITY_CONFLICT"
    status_code = 409


class SimulatorDisabled(DomainError):
    code = "SIMULATOR_DISABLED"
    status_code = 503


class InvalidSimulatorKey(DomainError):
    code = "INVALID_SIMULATOR_KEY"
    status_code = 401


class VisionEventRejected(DomainError):
    code = "VISION_EVENT_REJECTED"
    status_code = 422


class DiscrepancyNotFound(DomainError):
    code = "DISCREPANCY_NOT_FOUND"
    status_code = 404


class NudgeNotFound(DomainError):
    code = "NUDGE_NOT_FOUND"
    status_code = 404


class CheckoutNotAllowed(DomainError):
    code = "CHECKOUT_NOT_ALLOWED"
    status_code = 409
