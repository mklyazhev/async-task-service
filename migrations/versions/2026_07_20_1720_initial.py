"""Initial task and outbox tables."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202607201720"
down_revision = None
branch_labels = None
depends_on = None


task_priority = postgresql.ENUM("LOW", "MEDIUM", "HIGH", name="task_priority")
task_status = postgresql.ENUM("NEW", "PENDING", "IN_PROGRESS", "COMPLETED", "FAILED", "CANCELLED", name="task_status")
outbox_status = postgresql.ENUM("NEW", "PROCESSING", "PUBLISHED", "RETRY", name="outbox_status")


def upgrade() -> None:
    task_priority.create(op.get_bind(), checkfirst=True)
    task_status.create(op.get_bind(), checkfirst=True)
    outbox_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "tasks",
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", task_priority, nullable=False),
        sa.Column("status", task_status, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("result", postgresql.JSONB()),
        sa.Column("error_message", sa.Text()),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_table(
        "outbox_events",
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("status", outbox_status, nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True)),
        sa.Column("locked_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_outbox_status_next_retry", "outbox_events", ["status", "next_retry_at"])


def downgrade() -> None:
    op.drop_index("ix_outbox_status_next_retry", table_name="outbox_events")
    op.drop_table("outbox_events")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_table("tasks")
    outbox_status.drop(op.get_bind(), checkfirst=True)
    task_status.drop(op.get_bind(), checkfirst=True)
    task_priority.drop(op.get_bind(), checkfirst=True)
