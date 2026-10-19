from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from app.schemas.reconciliation import ReconciliationRead


class CustomerNudgeAction(StrEnum):
    SCAN_NOW = "SCAN_NOW"
    I_RETURNED_IT = "I_RETURNED_IT"
    GET_HELP = "GET_HELP"


class NudgeActionRequest(BaseModel):
    action: CustomerNudgeAction


class NudgeActionResult(BaseModel):
    nudge_id: str
    action: CustomerNudgeAction
    message: str
    reconciliation: ReconciliationRead


class CheckoutRequest(BaseModel):
    payment_mode: str = "SIMULATED"


class CheckoutResult(BaseModel):
    approved: bool
    payment_mode: str
    session_status: str
    message: str
    reconciliation: ReconciliationRead
