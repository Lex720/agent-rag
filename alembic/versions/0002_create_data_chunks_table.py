"""create data_chunks table

Revision ID: 0002_create_data_chunks
Revises: 0001_enable_vector
Create Date: 2026-06-25

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_create_data_chunks"
down_revision: str | None = "0001_enable_vector"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS data_chunks (
            id        UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
            path      TEXT    NOT NULL,
            method    TEXT    NOT NULL,
            content   TEXT    NOT NULL,
            embedding VECTOR(1024),
            metadata  JSONB
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS data_chunks")
