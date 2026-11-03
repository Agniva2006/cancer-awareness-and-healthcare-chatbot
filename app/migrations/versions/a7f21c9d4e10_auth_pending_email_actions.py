"""auth phase 2: pending_email_actions table

Revision ID: a7f21c9d4e10
Revises: e9ac0e362329
Create Date: 2026-11-02

Single-use hashed tokens for email verification and password reset.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7f21c9d4e10"
down_revision: Union[str, None] = "e9ac0e362329"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pending_email_actions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_pending_email_actions_user_id"),
        "pending_email_actions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_pending_email_actions_token_hash"),
        "pending_email_actions",
        ["token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_pending_email_actions_token_hash"), table_name="pending_email_actions"
    )
    op.drop_index(
        op.f("ix_pending_email_actions_user_id"), table_name="pending_email_actions"
    )
    op.drop_table("pending_email_actions")
