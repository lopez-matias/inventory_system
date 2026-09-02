"""Create the initial inventory schema.

Revision ID: 20260901_0001
Revises:
Create Date: 2026-09-01 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260901_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_locations_is_active"), "locations", ["is_active"], unique=False)
    op.create_index(op.f("ix_locations_name"), "locations", ["name"], unique=True)

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("unit", sa.String(length=30), nullable=False),
        sa.Column("minimum_stock", sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("minimum_stock >= 0", name="ck_product_minimum_stock"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_products_category"), "products", ["category"], unique=False)
    op.create_index(op.f("ix_products_is_active"), "products", ["is_active"], unique=False)
    op.create_index(op.f("ix_products_name"), "products", ["name"], unique=False)
    op.create_index(op.f("ix_products_sku"), "products", ["sku"], unique=True)

    op.create_table(
        "inventory_stocks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("quantity >= 0", name="ck_inventory_quantity_nonnegative"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "location_id", name="uq_stock_product_location"),
    )
    op.create_index(op.f("ix_inventory_stocks_location_id"), "inventory_stocks", ["location_id"], unique=False)
    op.create_index(op.f("ix_inventory_stocks_product_id"), "inventory_stocks", ["product_id"], unique=False)

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("movement_type", sa.Enum("ENTRY", "EXIT", "ADJUSTMENT", "TRANSFER", name="movement_type", native_enum=False, length=20, create_constraint=True), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("source_location_id", sa.Integer(), nullable=True),
        sa.Column("destination_location_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("quantity != 0", name="ck_movement_quantity_nonzero"),
        sa.CheckConstraint(
            "(movement_type = 'ENTRY' AND quantity > 0 AND source_location_id IS NULL "
            "AND destination_location_id IS NOT NULL) OR "
            "(movement_type = 'EXIT' AND quantity > 0 AND source_location_id IS NOT NULL "
            "AND destination_location_id IS NULL) OR "
            "(movement_type = 'TRANSFER' AND quantity > 0 AND source_location_id IS NOT NULL "
            "AND destination_location_id IS NOT NULL "
            "AND source_location_id <> destination_location_id) OR "
            "(movement_type = 'ADJUSTMENT' AND source_location_id IS NULL "
            "AND destination_location_id IS NOT NULL)",
            name="ck_movement_structure",
        ),
        sa.ForeignKeyConstraint(["destination_location_id"], ["locations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_location_id"], ["locations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_stock_movements_destination_location_id"), "stock_movements", ["destination_location_id"], unique=False)
    op.create_index(op.f("ix_stock_movements_product_id"), "stock_movements", ["product_id"], unique=False)
    op.create_index(op.f("ix_stock_movements_source_location_id"), "stock_movements", ["source_location_id"], unique=False)
    op.create_index(op.f("ix_stock_movements_timestamp"), "stock_movements", ["timestamp"], unique=False)
    op.create_index("ix_movements_product_timestamp", "stock_movements", ["product_id", "timestamp"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_movements_product_timestamp", table_name="stock_movements")
    op.drop_index(op.f("ix_stock_movements_timestamp"), table_name="stock_movements")
    op.drop_index(op.f("ix_stock_movements_source_location_id"), table_name="stock_movements")
    op.drop_index(op.f("ix_stock_movements_product_id"), table_name="stock_movements")
    op.drop_index(op.f("ix_stock_movements_destination_location_id"), table_name="stock_movements")
    op.drop_table("stock_movements")
    op.drop_index(op.f("ix_inventory_stocks_product_id"), table_name="inventory_stocks")
    op.drop_index(op.f("ix_inventory_stocks_location_id"), table_name="inventory_stocks")
    op.drop_table("inventory_stocks")
    op.drop_index(op.f("ix_products_sku"), table_name="products")
    op.drop_index(op.f("ix_products_name"), table_name="products")
    op.drop_index(op.f("ix_products_is_active"), table_name="products")
    op.drop_index(op.f("ix_products_category"), table_name="products")
    op.drop_table("products")
    op.drop_index(op.f("ix_locations_name"), table_name="locations")
    op.drop_index(op.f("ix_locations_is_active"), table_name="locations")
    op.drop_table("locations")
