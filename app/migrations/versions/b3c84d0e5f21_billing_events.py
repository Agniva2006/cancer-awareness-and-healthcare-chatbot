"""phase 3 billing: billing_events idempotency table

Revision ID: b3c84d0e5f21
Revises: a7f21c9d4e10
Create Date: 2026-11-02

Guards against duplicate webhook deliveries (provider event ID is unique).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3c84d0e5f21"
down_revision: Union[str, None] = "a7f21c9d4e10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "billing_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("provider_event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_billing_events_provider_event_id"),
        "billing_events",
        ["provider_event_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_billing_events_provider_event_id"), table_name="billing_events"
    )
    op.drop_table("billing_events")
