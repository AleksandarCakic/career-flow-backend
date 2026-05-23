"""add lead.notes

Revision ID: d2a14f3b8e91
Revises: a87b526949f3
Create Date: 2026-05-23 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2a14f3b8e91"
down_revision: str | Sequence[str] | None = "a87b526949f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("leads", sa.Column("notes", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("leads", "notes")
