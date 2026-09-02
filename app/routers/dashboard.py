from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.database import get_db
from app.models import InventoryStock, Location, Product, StockMovement
from app.schemas import (
    DashboardRead,
    LocationStockSummary,
    LowStockProduct,
)
from app.services.inventory import movement_to_read


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardRead)
def get_dashboard(db: Session = Depends(get_db)):
    active_products = db.scalar(
        select(func.count(Product.id)).where(Product.is_active.is_(True))
    ) or 0
    total_inventory_units = db.scalar(select(func.coalesce(func.sum(InventoryStock.quantity), 0)))

    product_total = func.coalesce(func.sum(InventoryStock.quantity), 0).label("total_quantity")
    low_stock_rows = db.execute(
        select(Product, product_total)
        .outerjoin(InventoryStock, InventoryStock.product_id == Product.id)
        .where(Product.is_active.is_(True))
        .group_by(Product.id)
        .having(product_total < Product.minimum_stock)
        .order_by((Product.minimum_stock - product_total).desc(), Product.name)
    ).all()
    low_stock_products = [
        LowStockProduct(
            product_id=product.id,
            sku=product.sku,
            name=product.name,
            unit=product.unit,
            minimum_stock=product.minimum_stock,
            total_quantity=total,
        )
        for product, total in low_stock_rows
    ]

    location_total = func.coalesce(func.sum(InventoryStock.quantity), 0).label("total_quantity")
    location_rows = db.execute(
        select(Location, location_total)
        .outerjoin(InventoryStock, InventoryStock.location_id == Location.id)
        .where(Location.is_active.is_(True))
        .group_by(Location.id)
        .order_by(location_total.desc(), Location.name)
    ).all()
    stock_by_location = [
        LocationStockSummary(
            location_id=location.id,
            location_name=location.name,
            total_quantity=total,
        )
        for location, total in location_rows
    ]

    recent_movements = db.scalars(
        select(StockMovement)
        .options(
            joinedload(StockMovement.product),
            joinedload(StockMovement.source_location),
            joinedload(StockMovement.destination_location),
        )
        .order_by(StockMovement.timestamp.desc(), StockMovement.id.desc())
        .limit(get_settings().recent_movements_limit)
    ).all()

    return DashboardRead(
        active_products=active_products,
        total_inventory_units=Decimal(total_inventory_units),
        low_stock_count=len(low_stock_products),
        low_stock_products=low_stock_products,
        recent_movements=[movement_to_read(item) for item in recent_movements],
        stock_by_location=stock_by_location,
    )
