from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import DomainError
from app.models import Product
from app.schemas import ProductCreate, ProductRead, ProductUpdate


router = APIRouter(prefix="/products", tags=["Products"])


def _get_product(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise DomainError("El producto no existe.", 404, "product_not_found")
    return product


@router.get("", response_model=list[ProductRead])
def list_products(
    search: str | None = Query(default=None, max_length=160),
    active: bool | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
):
    statement = select(Product).order_by(Product.name)
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(or_(Product.name.ilike(term), Product.sku.ilike(term)))
    if active is not None:
        statement = statement.where(Product.is_active == active)
    if category:
        statement = statement.where(func.lower(Product.category) == category.strip().lower())
    return db.scalars(statement).all()


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    product = Product(**data.model_dump())
    db.add(product)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DomainError("Ya existe un producto con ese SKU.", 409, "duplicate_sku") from exc
    db.refresh(product)
    return product


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: Session = Depends(get_db)):
    return _get_product(db, product_id)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(product_id: int, data: ProductUpdate, db: Session = Depends(get_db)):
    product = _get_product(db, product_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DomainError("Ya existe un producto con ese SKU.", 409, "duplicate_sku") from exc
    db.refresh(product)
    return product


@router.delete("/{product_id}", response_model=ProductRead)
def deactivate_product(product_id: int, db: Session = Depends(get_db)):
    product = _get_product(db, product_id)
    product.is_active = False
    db.commit()
    db.refresh(product)
    return product
