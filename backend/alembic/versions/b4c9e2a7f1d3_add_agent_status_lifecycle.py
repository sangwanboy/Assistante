"""Add agent status lifecycle column

Revision ID: b4c9e2a7f1d3
Revises: 9f32a1b6aa10
Create Date: 2026-03-12 18:00:00.000000

Adds a `status` VARCHAR(20) column to the `agents` table supporting
lifecycle states: active | idle | paused | deleted.

- active  — fully operational, receives tasks
- idle    — waiting; capacity still reserved
- paused  — suspended; capacity still reserved
- deleted — soft-deleted; capacity will be freed via Redis SREM

Only agents with status='deleted' free agent capacity.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b4c9e2a7f1d3"
down_revision: Union[str, None] = "9f32a1b6aa10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("agents")}

    if "status" not in columns:
        op.add_column(
            "agents",
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default="active",
            ),
        )
        # Backfill: set status based on existing is_active flag
        op.execute(
            "UPDATE agents SET status = CASE WHEN is_active THEN 'active' ELSE 'paused' END"
        )
        # Remove server default after backfill (keep runtime default on model)
        if bind.engine.name != "sqlite":
            op.alter_column("agents", "status", server_default=None)

    # Add index if it doesn't already exist
    indexes = {idx["name"] for idx in inspector.get_indexes("agents")}
    if "ix_agents_status" not in indexes:
        op.create_index("ix_agents_status", "agents", ["status"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    indexes = {idx["name"] for idx in inspector.get_indexes("agents")}
    if "ix_agents_status" in indexes:
        op.drop_index("ix_agents_status", table_name="agents")

    columns = {col["name"] for col in inspector.get_columns("agents")}
    if "status" in columns:
        op.drop_column("agents", "status")
