"""enable vector extension

Revision ID: 0001_enable_vector
Revises:
Create Date: 2026-06-25

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001_enable_vector"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Requires superuser on standard Postgres. On Supabase the postgres user has this privilege.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    # Intentionally omits CASCADE: dropping the extension while dependent objects exist
    # (e.g. other pgvector tables in a shared Supabase DB) should fail loudly rather than
    # silently remove unrelated schema.
    op.execute("DROP EXTENSION IF EXISTS vector")
