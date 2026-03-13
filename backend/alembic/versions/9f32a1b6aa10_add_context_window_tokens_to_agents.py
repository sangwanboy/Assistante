"""Add context_window_tokens to agents

Revision ID: 9f32a1b6aa10
Revises: 2442c38136ed
Create Date: 2026-03-12 12:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f32a1b6aa10"
down_revision: Union[str, None] = "2442c38136ed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("agents")}
    if "context_window_tokens" not in columns:
        op.add_column(
            "agents",
            sa.Column("context_window_tokens", sa.Integer(), nullable=False, server_default="256000"),
        )
        op.alter_column("agents", "context_window_tokens", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("agents")}
    if "context_window_tokens" in columns:
        op.drop_column("agents", "context_window_tokens")
