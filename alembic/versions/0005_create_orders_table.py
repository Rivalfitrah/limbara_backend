"""Create orders and order_items tables for Midtrans checkout and shipping.

Revision ID: 0005_create_orders_table
Revises: 0004_create_products_table
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_create_orders_table"
down_revision = "0004_create_products_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_number", sa.String(length=50), nullable=False),
        sa.Column("buyer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="PENDING", nullable=False),
        sa.Column("total_product_amount", sa.Integer(), server_default="0", nullable=False),
        sa.Column("shipping_cost", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_amount", sa.Integer(), server_default="0", nullable=False),
        sa.Column("courier", sa.String(length=50), nullable=False),
        sa.Column("courier_service", sa.String(length=50), nullable=False),
        sa.Column("recipient_name", sa.String(length=120), nullable=False),
        sa.Column("recipient_phone", sa.String(length=30), nullable=False),
        sa.Column("shipping_address", sa.Text(), nullable=False),
        sa.Column("shipping_province", sa.String(length=100), nullable=False),
        sa.Column("shipping_city", sa.String(length=100), nullable=False),
        sa.Column("shipping_postal_code", sa.String(length=20), nullable=True),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.Column("snap_token", sa.String(length=255), nullable=True),
        sa.Column("snap_redirect_url", sa.String(length=512), nullable=True),
        sa.Column("midtrans_transaction_id", sa.String(length=100), nullable=True),
        sa.Column("payment_type", sa.String(length=50), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_number", name="uq_orders_order_number"),
    )
    op.create_index("ix_orders_order_number", "orders", ["order_number"], unique=True)
    op.create_index("ix_orders_buyer_id", "orders", ["buyer_id"], unique=False)
    op.create_index("ix_orders_shop_id", "orders", ["shop_id"], unique=False)
    op.create_index("ix_orders_status", "orders", ["status"], unique=False)

    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_name", sa.String(length=120), nullable=False),
        sa.Column("product_image", sa.String(length=512), nullable=True),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1", nullable=False),
        sa.Column("subtotal", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"], unique=False)
    op.create_index("ix_order_items_product_id", "order_items", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_order_items_product_id", table_name="order_items")
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")

    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_orders_shop_id", table_name="orders")
    op.drop_index("ix_orders_buyer_id", table_name="orders")
    op.drop_index("ix_orders_order_number", table_name="orders")
    op.drop_table("orders")
