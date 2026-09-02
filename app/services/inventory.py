from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import DomainError
from app.models import InventoryStock, Location, MovementType, Product, StockMovement
from app.schemas import MovementCreate, MovementRead


def _get_active_product(session: Session, product_id: int) -> Product:
    product = session.scalar(select(Product).where(Product.id == product_id).with_for_update())
    if product is None:
        raise DomainError("El producto no existe.", 404, "product_not_found")
    if not product.is_active:
        raise DomainError("No se pueden registrar movimientos para un producto inactivo.")
    return product


def _get_active_location(session: Session, location_id: int) -> Location:
    location = session.scalar(select(Location).where(Location.id == location_id).with_for_update())
    if location is None:
        raise DomainError("La ubicación no existe.", 404, "location_not_found")
    if not location.is_active:
        raise DomainError("No se pueden registrar movimientos en una ubicación inactiva.")
    return location


def _get_stock(session: Session, product_id: int, location_id: int) -> InventoryStock:
    stock = session.scalar(
        select(InventoryStock)
        .where(
            InventoryStock.product_id == product_id,
            InventoryStock.location_id == location_id,
        )
        .with_for_update()
    )
    if stock is None:
        stock = InventoryStock(
            product_id=product_id,
            location_id=location_id,
            quantity=Decimal("0"),
        )
        session.add(stock)
        session.flush()
    return stock


def _subtract(stock: InventoryStock, quantity: Decimal) -> None:
    if stock.quantity < quantity:
        raise DomainError(
            f"Stock insuficiente. Disponible: {stock.quantity}.",
            409,
            "insufficient_stock",
        )
    stock.quantity -= quantity


def create_movement(session: Session, data: MovementCreate) -> StockMovement:
    """Apply a movement and keep its history in a single database transaction."""
    with session.begin():
        product = _get_active_product(session, data.product_id)

        location_ids = sorted(
            {
                location_id
                for location_id in (data.source_location_id, data.destination_location_id)
                if location_id is not None
            }
        )
        locked_locations = {
            location_id: _get_active_location(session, location_id)
            for location_id in location_ids
        }
        source_location = locked_locations.get(data.source_location_id)
        destination_location = locked_locations.get(data.destination_location_id)

        if data.movement_type == MovementType.ENTRY:
            destination = _get_stock(session, data.product_id, data.destination_location_id)
            destination.quantity += data.quantity
        elif data.movement_type == MovementType.EXIT:
            source = _get_stock(session, data.product_id, data.source_location_id)
            _subtract(source, data.quantity)
        elif data.movement_type == MovementType.TRANSFER:
            # Lock in deterministic order to reduce deadlock risk between transfers.
            location_ids = sorted([data.source_location_id, data.destination_location_id])
            locked_stocks = {
                location_id: _get_stock(session, data.product_id, location_id)
                for location_id in location_ids
            }
            _subtract(locked_stocks[data.source_location_id], data.quantity)
            locked_stocks[data.destination_location_id].quantity += data.quantity
        else:
            adjusted_stock = _get_stock(session, data.product_id, data.destination_location_id)
            if data.quantity < 0:
                _subtract(adjusted_stock, abs(data.quantity))
            else:
                adjusted_stock.quantity += data.quantity

        movement = StockMovement(
            movement_type=data.movement_type,
            product=product,
            quantity=data.quantity,
            source_location=source_location,
            destination_location=destination_location,
            notes=data.notes,
        )
        session.add(movement)
        session.flush()
    return movement


def movement_to_read(movement: StockMovement) -> MovementRead:
    return MovementRead(
        id=movement.id,
        movement_type=movement.movement_type,
        timestamp=movement.timestamp,
        quantity=movement.quantity,
        product_id=movement.product_id,
        product_sku=movement.product.sku,
        product_name=movement.product.name,
        source_location_id=movement.source_location_id,
        source_location_name=movement.source_location.name if movement.source_location else None,
        destination_location_id=movement.destination_location_id,
        destination_location_name=(
            movement.destination_location.name if movement.destination_location else None
        ),
        notes=movement.notes,
    )
