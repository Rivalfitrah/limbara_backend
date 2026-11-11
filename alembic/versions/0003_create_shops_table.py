"""Create shops table for marketplace foundation.

Revision ID: 0003_create_shops_table
Revises: 0002_auth_foundation
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_create_shops_table"
down_revision = "0002_auth_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shops",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("waste_focus", sa.String(length=255), nullable=True),
        sa.Column("province", sa.String(length=100), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("district", sa.String(length=100), nullable=True),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("postal_code", sa.String(length=10), nullable=True),
        sa.Column("phone_number", sa.String(length=25), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("courier_options", sa.JSON(), nullable=True),
        sa.Column("logo_url", sa.String(length=512), nullable=True),
        sa.Column("banner_url", sa.String(length=512), nullable=True),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_shops_user_id"),
        sa.UniqueConstraint("slug", name="uq_shops_slug"),
    )
    op.create_index("ix_shops_user_id", "shops", ["user_id"], unique=True)
    op.create_index("ix_shops_name", "shops", ["name"], unique=False)
    op.create_index("ix_shops_slug", "shops", ["slug"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_shops_slug", table_name="shops")
    op.drop_index("ix_shops_name", table_name="shops")
    op.drop_index("ix_shops_user_id", table_name="shops")
    op.drop_table("shops")
