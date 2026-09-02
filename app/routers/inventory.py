from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import InventoryStock, Location, Product
from app.schemas import InventoryRead


router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("", response_model=list[InventoryRead])
def list_inventory(
    product_id: int | None = None,
    location_id: int | None = None,
    low_stock: bool | None = None,
    db: Session = Depends(get_db),
):
    statement = (
        select(InventoryStock, Product, Location)
        .join(Product, Product.id == InventoryStock.product_id)
        .join(Location, Location.id == InventoryStock.location_id)
        .order_by(Product.name, Location.name)
    )
    if product_id is not None:
        statement = statement.where(InventoryStock.product_id == product_id)
    if location_id is not None:
        statement = statement.where(InventoryStock.location_id == location_id)
    if low_stock is not None:
        comparison = InventoryStock.quantity < Product.minimum_stock
        statement = statement.where(comparison if low_stock else ~comparison)

    return [
        InventoryRead(
            id=stock.id,
            product_id=product.id,
            product_sku=product.sku,
            product_name=product.name,
            unit=product.unit,
            minimum_stock=product.minimum_stock,
            location_id=location.id,
            location_name=location.name,
            quantity=stock.quantity,
            is_below_minimum=stock.quantity < product.minimum_stock,
            updated_at=stock.updated_at,
        )
        for stock, product, location in db.execute(statement).all()
    ]
