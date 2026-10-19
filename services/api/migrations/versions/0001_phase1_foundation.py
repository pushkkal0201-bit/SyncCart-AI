"""phase 1 foundation

Revision ID: 0001_phase1
Revises:
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_phase1"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("barcode", sa.String(64), nullable=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("category", sa.String(120), nullable=True),
        sa.Column("unit_price_minor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("expected_visual_class", sa.String(128), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("unit_price_minor >= 0", name="ck_product_price_nonnegative"),
        sa.UniqueConstraint("sku", name="uq_products_sku"),
        sa.UniqueConstraint("barcode", name="uq_products_barcode"),
    )
    op.create_index("ix_products_sku", "products", ["sku"])
    op.create_index("ix_products_barcode", "products", ["barcode"])

    op.create_table(
        "shopping_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("public_id", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checkout_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("public_id", name="uq_sessions_public_id"),
    )
    op.create_index("ix_sessions_status", "shopping_sessions", ["status"])
    op.create_index("ix_sessions_started_at", "shopping_sessions", ["started_at"])

    op.create_table(
        "cart_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("shopping_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity >= 0", name="ck_cart_quantity_nonnegative"),
        sa.CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_cart_confidence_range"),
        sa.UniqueConstraint("session_id", "product_id", "source", name="uq_cart_projection"),
    )
    op.create_index("ix_cart_session_source", "cart_items", ["session_id", "source"])

    op.create_table(
        "events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("shopping_sessions.id", ondelete="CASCADE"), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("event_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("sku", sa.String(64), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("correlation_id", sa.String(36), nullable=False),
        sa.Column("causation_id", sa.String(36), nullable=True),
        sa.Column("camera_id", sa.String(64), nullable=True),
        sa.Column("zone_id", sa.String(64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity IS NULL OR quantity > 0", name="ck_event_quantity_positive"),
        sa.CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_event_confidence_range"),
    )
    op.create_index("ix_events_session_created", "events", ["session_id", "created_at"])
    op.create_index("ix_events_type_created", "events", ["event_type", "created_at"])
    op.create_index("ix_events_correlation_id", "events", ["correlation_id"])


def downgrade() -> None:
    op.drop_table("events")
    op.drop_table("cart_items")
    op.drop_table("shopping_sessions")
    op.drop_table("products")
