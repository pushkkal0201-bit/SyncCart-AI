"""phase 2 digital cart

Revision ID: 0002_phase2
Revises: 0001_phase1
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_phase2"
down_revision: Union[str, None] = "0001_phase1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("shopping_sessions") as batch_op:
        batch_op.add_column(sa.Column("customer_token_hash", sa.String(64), nullable=True))
        batch_op.add_column(
            sa.Column("customer_token_expires_at", sa.DateTime(timezone=True), nullable=True)
        )

    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("shopping_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("operation", sa.String(48), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("response_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "session_id",
            "operation",
            "idempotency_key",
            name="uq_idempotency_session_operation_key",
        ),
    )
    op.create_index(
        "ix_idempotency_records_session_id",
        "idempotency_records",
        ["session_id"],
    )
    op.create_index(
        "ix_idempotency_records_created_at",
        "idempotency_records",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_table("idempotency_records")
    with op.batch_alter_table("shopping_sessions") as batch_op:
        batch_op.drop_column("customer_token_expires_at")
        batch_op.drop_column("customer_token_hash")
