"""Add multi-provider authentication and revocable sessions.

Revision ID: 0002_auth_foundation
Revises: 0001_baseline
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_auth_foundation"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.alter_column("users", "google_id", existing_type=sa.String(), nullable=True)

    op.create_table(
        "auth_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("provider_subject", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(provider = 'LOCAL' AND password_hash IS NOT NULL) OR "
            "(provider = 'GOOGLE' AND provider_subject IS NOT NULL AND password_hash IS NULL)",
            name="ck_auth_accounts_credentials",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_subject", name="uq_auth_accounts_provider_subject"),
        sa.UniqueConstraint("user_id", "provider", name="uq_auth_accounts_user_provider"),
    )
    op.create_index("ix_auth_accounts_user_id", "auth_accounts", ["user_id"], unique=False)

    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"], unique=False)
    op.create_index("ix_user_sessions_token_hash", "user_sessions", ["token_hash"], unique=True)
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"], unique=False)

    op.execute(
        """
        INSERT INTO auth_accounts (id, user_id, provider, provider_subject, password_hash, created_at)
        SELECT gen_random_uuid(), id, 'GOOGLE', google_id, NULL, created_at
        FROM users
        WHERE google_id IS NOT NULL
        ON CONFLICT (provider, provider_subject) DO NOTHING
        """
    )
    op.execute(
        "UPDATE users SET email_verified_at = created_at "
        "WHERE google_id IS NOT NULL AND email_verified_at IS NULL"
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM users WHERE google_id IS NULL) THEN
                RAISE EXCEPTION 'Cannot downgrade while manual users exist';
            END IF;
        END $$;
        """
    )
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_index("ix_user_sessions_token_hash", table_name="user_sessions")
    op.drop_index("ix_user_sessions_expires_at", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_index("ix_auth_accounts_user_id", table_name="auth_accounts")
    op.drop_table("auth_accounts")
    op.alter_column("users", "google_id", existing_type=sa.String(), nullable=False)
    op.drop_column("users", "updated_at")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "is_active")
    op.drop_column("users", "email_verified_at")
