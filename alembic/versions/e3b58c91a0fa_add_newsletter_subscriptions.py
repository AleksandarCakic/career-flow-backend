"""add newsletter_subscriptions

Revision ID: e3b58c91a0fa
Revises: d2a14f3b8e91
Create Date: 2026-05-23 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3b58c91a0fa"
down_revision: str | Sequence[str] | None = "d2a14f3b8e91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "newsletter_subscriptions",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("confirmation_token", sa.String(length=64), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unsubscribed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("posthog_distinct_id", sa.String(length=120), nullable=True),
        sa.Column("source", sa.String(length=80), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("confirmation_token"),
    )
    op.create_index(
        op.f("ix_newsletter_subscriptions_email"),
        "newsletter_subscriptions",
        ["email"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_newsletter_subscriptions_email"),
        table_name="newsletter_subscriptions",
    )
    op.drop_table("newsletter_subscriptions")
