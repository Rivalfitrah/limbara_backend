"""Create reviews table and add tracking fields to orders table.

Revision ID: 0006_create_reviews_table
Revises: 0005_create_orders_table
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_create_reviews_table"
down_revision = "0005_create_orders_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add tracking and completion fields to orders
    op.add_column("orders", sa.Column("tracking_number", sa.String(length=100), nullable=True))
    op.add_column("orders", sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))

    # 2. Create product_reviews table
    op.create_table(
        "product_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_name", sa.String(length=100), nullable=False),
        sa.Column("user_avatar", sa.String(length=512), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", "product_id", name="uq_order_product_review"),
    )
    op.create_index("ix_product_reviews_order_id", "product_reviews", ["order_id"], unique=False)
    op.create_index("ix_product_reviews_product_id", "product_reviews", ["product_id"], unique=False)
    op.create_index("ix_product_reviews_user_id", "product_reviews", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_product_reviews_user_id", table_name="product_reviews")
    op.drop_index("ix_product_reviews_product_id", table_name="product_reviews")
    op.drop_index("ix_product_reviews_order_id", table_name="product_reviews")
    op.drop_table("product_reviews")

    op.drop_column("orders", "completed_at")
    op.drop_column("orders", "shipped_at")
    op.drop_column("orders", "tracking_number")
