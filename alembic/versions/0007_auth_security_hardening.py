"""Add persistent auth rate limits and one-time OAuth states.

Revision ID: 0007_auth_security_hardening
Revises: 0006_create_reviews_table
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0007_auth_security_hardening"
down_revision = "0006_create_reviews_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_rate_limits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("identifier_hash", sa.String(length=64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("action", "identifier_hash", name="uq_auth_rate_limit_action_identifier"),
    )
    op.create_index("ix_auth_rate_limits_action", "auth_rate_limits", ["action"])
    op.create_index("ix_auth_rate_limits_identifier_hash", "auth_rate_limits", ["identifier_hash"])
    op.create_index("ix_auth_rate_limits_blocked_until", "auth_rate_limits", ["blocked_until"])

    op.create_table(
        "oauth_login_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_oauth_login_states_state_hash", "oauth_login_states", ["state_hash"], unique=True)
    op.create_index("ix_oauth_login_states_expires_at", "oauth_login_states", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_oauth_login_states_expires_at", table_name="oauth_login_states")
    op.drop_index("ix_oauth_login_states_state_hash", table_name="oauth_login_states")
    op.drop_table("oauth_login_states")
    op.drop_index("ix_auth_rate_limits_blocked_until", table_name="auth_rate_limits")
    op.drop_index("ix_auth_rate_limits_identifier_hash", table_name="auth_rate_limits")
    op.drop_index("ix_auth_rate_limits_action", table_name="auth_rate_limits")
    op.drop_table("auth_rate_limits")

