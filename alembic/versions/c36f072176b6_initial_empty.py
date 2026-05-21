"""initial empty

Revision ID: c36f072176b6
Revises:
Create Date: 2026-05-20 23:51:25.020306

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "c36f072176b6"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
