from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.exceptions import DomainError
from app.models import MovementType, StockMovement
from app.schemas import MovementCreate, MovementRead
from app.services.inventory import create_movement, movement_to_read


router = APIRouter(prefix="/movements", tags=["Movements"])


def _movement_query():
    return select(StockMovement).options(
        joinedload(StockMovement.product),
        joinedload(StockMovement.source_location),
        joinedload(StockMovement.destination_location),
    )


@router.get("", response_model=list[MovementRead])
def list_movements(
    product_id: int | None = None,
    location_id: int | None = None,
    movement_type: MovementType | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    statement = _movement_query().order_by(StockMovement.timestamp.desc(), StockMovement.id.desc())
    if product_id is not None:
        statement = statement.where(StockMovement.product_id == product_id)
    if location_id is not None:
        statement = statement.where(
            (StockMovement.source_location_id == location_id)
            | (StockMovement.destination_location_id == location_id)
        )
    if movement_type is not None:
        statement = statement.where(StockMovement.movement_type == movement_type)
    movements = db.scalars(statement.limit(limit)).all()
    return [movement_to_read(movement) for movement in movements]


@router.post("", response_model=MovementRead, status_code=status.HTTP_201_CREATED)
def register_movement(data: MovementCreate, db: Session = Depends(get_db)):
    return movement_to_read(create_movement(db, data))


@router.get("/{movement_id}", response_model=MovementRead)
def get_movement(movement_id: int, db: Session = Depends(get_db)):
    movement = db.scalar(_movement_query().where(StockMovement.id == movement_id))
    if movement is None:
        raise DomainError("El movimiento no existe.", 404, "movement_not_found")
    return movement_to_read(movement)
