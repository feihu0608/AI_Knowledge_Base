"""Create the initial multi-tenant knowledge platform schema."""
from __future__ import annotations

from alembic import op

from knowledge_persistence.base import Base
import knowledge_persistence.models  # noqa: F401

revision = "20260915_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    for table in Base.metadata.sorted_tables:
        table.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(Base.metadata.sorted_tables):
        table.drop(bind=bind, checkfirst=True)
