from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import DomainError
from app.models import Location
from app.schemas import LocationCreate, LocationRead, LocationUpdate


router = APIRouter(prefix="/locations", tags=["Locations"])


def _get_location(db: Session, location_id: int) -> Location:
    location = db.get(Location, location_id)
    if location is None:
        raise DomainError("La ubicación no existe.", 404, "location_not_found")
    return location


@router.get("", response_model=list[LocationRead])
def list_locations(
    search: str | None = Query(default=None, max_length=160),
    active: bool | None = None,
    db: Session = Depends(get_db),
):
    statement = select(Location).order_by(Location.name)
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(
            or_(Location.name.ilike(term), Location.description.ilike(term))
        )
    if active is not None:
        statement = statement.where(Location.is_active == active)
    return db.scalars(statement).all()


@router.post("", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
def create_location(data: LocationCreate, db: Session = Depends(get_db)):
    location = Location(**data.model_dump())
    db.add(location)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DomainError(
            "Ya existe una ubicación con ese nombre.", 409, "duplicate_location"
        ) from exc
    db.refresh(location)
    return location


@router.get("/{location_id}", response_model=LocationRead)
def get_location(location_id: int, db: Session = Depends(get_db)):
    return _get_location(db, location_id)


@router.patch("/{location_id}", response_model=LocationRead)
def update_location(location_id: int, data: LocationUpdate, db: Session = Depends(get_db)):
    location = _get_location(db, location_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(location, key, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DomainError(
            "Ya existe una ubicación con ese nombre.", 409, "duplicate_location"
        ) from exc
    db.refresh(location)
    return location


@router.delete("/{location_id}", response_model=LocationRead)
def deactivate_location(location_id: int, db: Session = Depends(get_db)):
    location = _get_location(db, location_id)
    location.is_active = False
    db.commit()
    db.refresh(location)
    return location
