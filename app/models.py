from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MovementType(str, Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    ADJUSTMENT = "ADJUSTMENT"
    TRANSFER = "TRANSFER"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    minimum_stock: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    stocks: Mapped[list["InventoryStock"]] = relationship(back_populates="product")
    movements: Mapped[list["StockMovement"]] = relationship(back_populates="product")

    __table_args__ = (CheckConstraint("minimum_stock >= 0", name="ck_product_minimum_stock"),)


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    source_movements: Mapped[list["StockMovement"]] = relationship(
        foreign_keys="StockMovement.source_location_id", back_populates="source_location"
    )
    destination_movements: Mapped[list["StockMovement"]] = relationship(
        foreign_keys="StockMovement.destination_location_id", back_populates="destination_location"
    )
    stocks: Mapped[list["InventoryStock"]] = relationship(back_populates="location")


class InventoryStock(Base):
    __tablename__ = "inventory_stocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    product: Mapped[Product] = relationship(back_populates="stocks")
    location: Mapped[Location] = relationship(back_populates="stocks")

    __table_args__ = (
        UniqueConstraint("product_id", "location_id", name="uq_stock_product_location"),
        CheckConstraint("quantity >= 0", name="ck_inventory_quantity_nonnegative"),
    )


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    movement_type: Mapped[MovementType] = mapped_column(
        SqlEnum(
            MovementType,
            name="movement_type",
            native_enum=False,
            length=20,
            create_constraint=True,
        ),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_location_id: Mapped[int | None] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"), index=True
    )
    destination_location_id: Mapped[int | None] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"), index=True
    )
    notes: Mapped[str | None] = mapped_column(Text)

    product: Mapped[Product] = relationship(back_populates="movements")
    source_location: Mapped[Location | None] = relationship(
        foreign_keys=[source_location_id], back_populates="source_movements"
    )
    destination_location: Mapped[Location | None] = relationship(
        foreign_keys=[destination_location_id], back_populates="destination_movements"
    )

    __table_args__ = (
        CheckConstraint("quantity != 0", name="ck_movement_quantity_nonzero"),
        CheckConstraint(
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
        Index("ix_movements_product_timestamp", "product_id", "timestamp"),
    )
