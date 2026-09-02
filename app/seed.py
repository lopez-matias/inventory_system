"""Load a small, idempotent data set for local demonstrations."""

from decimal import Decimal

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import Location, Product, StockMovement
from app.schemas import MovementCreate
from app.models import MovementType
from app.services.inventory import create_movement


PRODUCTS = [
    {
        "sku": "EMB-CAJA-M",
        "name": "Caja de cartón mediana",
        "description": "Caja para preparación y despacho de pedidos.",
        "category": "Embalaje",
        "unit": "unidad",
        "minimum_stock": Decimal("40"),
    },
    {
        "sku": "ETQ-TERM-80",
        "name": "Rollo de etiquetas térmicas",
        "description": "Etiquetas de 80 mm para identificación interna.",
        "category": "Etiquetado",
        "unit": "rollo",
        "minimum_stock": Decimal("20"),
    },
    {
        "sku": "SEG-GUA-NIT-M",
        "name": "Guantes de nitrilo talle M",
        "description": "Caja de guantes para tareas de manipulación.",
        "category": "Seguridad",
        "unit": "caja",
        "minimum_stock": Decimal("30"),
    },
]

LOCATIONS = [
    {"name": "Depósito central", "description": "Almacenamiento y recepción principal."},
    {"name": "Tienda", "description": "Existencias disponibles en el punto de venta."},
]


def run_seed() -> None:
    with SessionLocal() as db:
        for data in PRODUCTS:
            if db.scalar(select(Product).where(Product.sku == data["sku"])) is None:
                db.add(Product(**data))
        for data in LOCATIONS:
            if db.scalar(select(Location).where(Location.name == data["name"])) is None:
                db.add(Location(**data))
        db.commit()

        movement_count = db.scalar(select(func.count(StockMovement.id))) or 0
        products = {item.sku: item.id for item in db.scalars(select(Product)).all()}
        locations = {item.name: item.id for item in db.scalars(select(Location)).all()}

    if movement_count == 0:
        demo_movements = [
            MovementCreate(movement_type=MovementType.ENTRY, product_id=products["EMB-CAJA-M"], quantity=120, destination_location_id=locations["Depósito central"], notes="Carga inicial de demostración"),
            MovementCreate(movement_type=MovementType.ENTRY, product_id=products["ETQ-TERM-80"], quantity=65, destination_location_id=locations["Depósito central"], notes="Carga inicial de demostración"),
            MovementCreate(movement_type=MovementType.ENTRY, product_id=products["SEG-GUA-NIT-M"], quantity=15, destination_location_id=locations["Depósito central"], notes="Carga inicial por debajo del mínimo"),
            MovementCreate(movement_type=MovementType.TRANSFER, product_id=products["EMB-CAJA-M"], quantity=25, source_location_id=locations["Depósito central"], destination_location_id=locations["Tienda"], notes="Reposición del punto de venta"),
        ]
        with SessionLocal() as db:
            for movement in demo_movements:
                create_movement(db, movement)

    print("Datos de demostración listos.")


if __name__ == "__main__":
    run_seed()
