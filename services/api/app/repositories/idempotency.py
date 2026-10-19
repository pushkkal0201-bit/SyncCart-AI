from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.idempotency import IdempotencyRecord


class IdempotencyRepository:
    def get(
        self,
        db: Session,
        *,
        session_id: str,
        operation: str,
        idempotency_key: str,
    ) -> IdempotencyRecord | None:
        statement = select(IdempotencyRecord).where(
            IdempotencyRecord.session_id == session_id,
            IdempotencyRecord.operation == operation,
            IdempotencyRecord.idempotency_key == idempotency_key,
        )
        return db.scalar(statement)

    def add(self, db: Session, record: IdempotencyRecord) -> IdempotencyRecord:
        db.add(record)
        db.flush()
        return record
