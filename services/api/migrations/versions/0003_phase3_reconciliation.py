"""phase 3 reconciliation engine

Revision ID: 0003_phase3
Revises: 0002_phase2
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_phase3"
down_revision: Union[str, None] = "0002_phase2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "discrepancies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("shopping_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("physical_quantity", sa.Integer(), nullable=False),
        sa.Column("digital_quantity", sa.Integer(), nullable=False),
        sa.Column("difference", sa.Integer(), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("vision_confidence", sa.Float(), nullable=True),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("correlation_id", sa.String(36), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("grace_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("risk_score >= 0 AND risk_score <= 1", name="ck_discrepancy_risk_range"),
        sa.CheckConstraint(
            "vision_confidence IS NULL OR (vision_confidence >= 0 AND vision_confidence <= 1)",
            name="ck_discrepancy_vision_confidence_range",
        ),
    )
    op.create_index("ix_discrepancies_session_id", "discrepancies", ["session_id"])
    op.create_index("ix_discrepancies_product_id", "discrepancies", ["product_id"])
    op.create_index("ix_discrepancies_sku", "discrepancies", ["sku"])
    op.create_index("ix_discrepancies_status", "discrepancies", ["status"])
    op.create_index("ix_discrepancies_correlation_id", "discrepancies", ["correlation_id"])

    op.create_table(
        "event_matches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("shopping_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("physical_event_id", sa.String(36), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("digital_event_id", sa.String(36), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("matched_quantity", sa.Integer(), nullable=False),
        sa.Column("match_confidence", sa.Float(), nullable=False),
        sa.Column("matched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("physical_event_id", name="uq_event_match_physical"),
        sa.UniqueConstraint("digital_event_id", name="uq_event_match_digital"),
        sa.CheckConstraint("matched_quantity > 0", name="ck_event_match_quantity_positive"),
        sa.CheckConstraint("match_confidence >= 0 AND match_confidence <= 1", name="ck_event_match_confidence_range"),
    )
    op.create_index("ix_event_matches_session_id", "event_matches", ["session_id"])
    op.create_index("ix_event_matches_sku", "event_matches", ["sku"])

    op.create_table(
        "nudges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("discrepancy_id", sa.String(36), sa.ForeignKey("discrepancies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("shopping_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("message", sa.String(240), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("action", sa.String(64), nullable=True),
    )
    op.create_index("ix_nudges_discrepancy_id", "nudges", ["discrepancy_id"])
    op.create_index("ix_nudges_session_id", "nudges", ["session_id"])
    op.create_index("ix_nudges_sku", "nudges", ["sku"])


def downgrade() -> None:
    op.drop_table("nudges")
    op.drop_table("event_matches")
    op.drop_table("discrepancies")
