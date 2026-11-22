"""Initial training schema."""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    status = postgresql.ENUM(
        "learning", "quiz", "completed", "cancelled", name="session_status", create_type=False
    )
    status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "training_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("display_name", sa.String(255)),
        sa.Column("material_slug", sa.String(100), nullable=False),
        sa.Column("material_version", sa.String(50), nullable=False),
        sa.Column("status", status, nullable=False),
        sa.Column("current_question", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checked_answers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_answers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_training_sessions_telegram_user_id", "training_sessions", ["telegram_user_id"])
    op.create_table(
        "training_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("training_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("material_slug", sa.String(100), nullable=False),
        sa.Column("material_version", sa.String(50), nullable=False),
        sa.Column("checked_answers", sa.Integer(), nullable=False),
        sa.Column("correct_answers", sa.Integer(), nullable=False),
        sa.Column("score_percent", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("session_id", name="uq_training_results_session_id"),
    )
    op.create_index("ix_training_results_telegram_user_id", "training_results", ["telegram_user_id"])
    op.create_table(
        "processed_updates",
        sa.Column("update_id", sa.BigInteger(), primary_key=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("processed_updates")
    op.drop_index("ix_training_results_telegram_user_id", table_name="training_results")
    op.drop_table("training_results")
    op.drop_index("ix_training_sessions_telegram_user_id", table_name="training_sessions")
    op.drop_table("training_sessions")
    sa.Enum(name="session_status").drop(op.get_bind(), checkfirst=True)
