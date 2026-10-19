from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models.event import DomainEvent, EventType
from app.models.mixins import utcnow
from app.models.reconciliation import Discrepancy, DiscrepancyStatus, EventMatch, Nudge
from app.models.shopping_session import SessionStatus, ShoppingSession
from app.schemas.event import EventRead
from app.schemas.monitoring import (
    MonitoringMetricsRead,
    MonitoringNoticeRead,
    MonitoringOverviewRead,
    MonitoringSessionInspectorRead,
    ServiceHealthRead,
    ServiceState,
)
from app.services.monitoring_telemetry import telemetry_store
from app.services.reconciliation import ReconciliationService
from app.repositories.sessions import SessionRepository
from app.core.exceptions import DomainError


class MonitoringSessionNotFound(DomainError):
    code = "MONITORING_SESSION_NOT_FOUND"
    status_code = 404


class MonitoringService:
    def __init__(self) -> None:
        self.reconciliation = ReconciliationService()
        self.sessions = SessionRepository()

    @staticmethod
    def _count(db: Session, statement) -> int:
        value = db.scalar(statement)
        return int(value or 0)

    def _metrics(self, db: Session) -> MonitoringMetricsRead:
        active_statuses = tuple(
            status.value
            for status in SessionStatus
            if status not in {SessionStatus.COMPLETED, SessionStatus.CHECKOUT_APPROVED}
        )
        open_discrepancy_statuses = (
            DiscrepancyStatus.VERIFYING.value,
            DiscrepancyStatus.NUDGE_SENT.value,
            DiscrepancyStatus.REVIEW_REQUIRED.value,
        )
        return MonitoringMetricsRead(
            total_sessions=self._count(db, select(func.count()).select_from(ShoppingSession)),
            active_sessions=self._count(
                db,
                select(func.count()).select_from(ShoppingSession).where(ShoppingSession.status.in_(active_statuses)),
            ),
            total_events=self._count(db, select(func.count()).select_from(DomainEvent)),
            vision_events=self._count(
                db,
                select(func.count()).select_from(DomainEvent).where(
                    DomainEvent.event_type.in_(
                        (
                            EventType.VISION_PICKUP.value,
                            EventType.VISION_RETURN.value,
                            EventType.VISION_COUNT_CHANGED.value,
                        )
                    )
                ),
            ),
            customer_scan_events=self._count(
                db,
                select(func.count()).select_from(DomainEvent).where(
                    DomainEvent.event_type == EventType.PRODUCT_SCANNED.value
                ),
            ),
            match_confirmed_events=self._count(
                db,
                select(func.count()).select_from(DomainEvent).where(
                    DomainEvent.event_type == EventType.MATCH_CONFIRMED.value
                ),
            ),
            open_discrepancies=self._count(
                db,
                select(func.count()).select_from(Discrepancy).where(
                    Discrepancy.status.in_(open_discrepancy_statuses)
                ),
            ),
            event_matches=self._count(db, select(func.count()).select_from(EventMatch)),
            nudges_sent=self._count(db, select(func.count()).select_from(Nudge)),
            reviews_required=self._count(
                db,
                select(func.count()).select_from(DomainEvent).where(
                    DomainEvent.event_type == EventType.REVIEW_REQUIRED.value
                ),
            ),
            checkouts_approved=self._count(
                db,
                select(func.count()).select_from(DomainEvent).where(
                    DomainEvent.event_type == EventType.CHECKOUT_APPROVED.value
                ),
            ),
        )

    @staticmethod
    def recent_events(db: Session, *, limit: int = 40, event_type: str | None = None) -> list[EventRead]:
        statement = select(DomainEvent)
        if event_type:
            statement = statement.where(DomainEvent.event_type == event_type)
        statement = statement.order_by(DomainEvent.created_at.desc()).limit(limit)
        return [EventRead.model_validate(item, from_attributes=True) for item in db.scalars(statement).all()]

    def _services(self, *, now: datetime) -> list[ServiceHealthRead]:
        camera = telemetry_store.camera()
        vision = telemetry_store.vision()
        return [
            ServiceHealthRead(
                name="API",
                status=ServiceState.HEALTHY,
                detail="FastAPI process is responding.",
                last_checked_at=now,
            ),
            ServiceHealthRead(
                name="Database",
                status=ServiceState.HEALTHY,
                detail=f"Transactional database connected via {engine.url.get_backend_name()}.",
                last_checked_at=now,
            ),
            ServiceHealthRead(
                name="Reconciliation",
                status=ServiceState.HEALTHY,
                detail="Cart reconciliation engine is available.",
                last_checked_at=now,
            ),
            ServiceHealthRead(
                name="Camera",
                status=camera.status,
                detail=camera.note or f"{camera.camera_id} telemetry received.",
                last_checked_at=camera.updated_at,
            ),
            ServiceHealthRead(
                name="Vision",
                status=vision.status,
                detail=vision.note or "Vision runtime telemetry received.",
                last_checked_at=vision.updated_at,
            ),
        ]

    def overview(self, db: Session) -> MonitoringOverviewRead:
        now = utcnow()
        camera = telemetry_store.camera()
        vision = telemetry_store.vision()
        notices: list[MonitoringNoticeRead] = []
        if camera.status == ServiceState.NOT_CONFIGURED:
            notices.append(
                MonitoringNoticeRead(
                    level="INFO",
                    title="Retail camera not connected yet",
                    detail="Monitoring accepts telemetry from CCTV/NVR, IP camera, webcam, recorded-video, or Phone 1 demo sources through the same edge Vision contract.",
                )
            )
        if vision.status == ServiceState.NOT_CONFIGURED:
            notices.append(
                MonitoringNoticeRead(
                    level="INFO",
                    title="Vision runtime not connected yet",
                    detail="Runtime metrics are emitted only from actual detector execution. The simulator remains available as a deterministic demonstration profile.",
                )
            )
        if camera.status in {ServiceState.DEGRADED, ServiceState.OFFLINE}:
            notices.append(
                MonitoringNoticeRead(
                    level="WARN",
                    title=f"Camera {camera.status.value.lower()}",
                    detail=camera.note or "Automatic physical evidence should be treated cautiously.",
                )
            )
        if vision.status in {ServiceState.DEGRADED, ServiceState.OFFLINE}:
            notices.append(
                MonitoringNoticeRead(
                    level="WARN",
                    title=f"Vision {vision.status.value.lower()}",
                    detail=vision.note or "Automatic escalation should fail safe while Vision is unhealthy.",
                )
            )
        return MonitoringOverviewRead(
            generated_at=now,
            services=self._services(now=now),
            metrics=self._metrics(db),
            camera=camera,
            vision=vision,
            recent_events=self.recent_events(db, limit=30),
            notices=notices,
        )

    def inspect_session(self, db: Session, *, session_id: str) -> MonitoringSessionInspectorRead:
        session = self.sessions.get(db, session_id)
        if session is None:
            raise MonitoringSessionNotFound(f"Session '{session_id}' was not found")
        return MonitoringSessionInspectorRead(
            reconciliation=self.reconciliation.get_status(db, session_id=session_id),
            events=[EventRead.model_validate(item, from_attributes=True) for item in self.sessions.list_events(db, session_id)],
        )
