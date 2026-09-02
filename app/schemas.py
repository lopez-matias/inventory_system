from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import MovementType


class ProductBase(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    category: str = Field(min_length=1, max_length=100)
    unit: str = Field(min_length=1, max_length=30)
    minimum_stock: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=3)
    is_active: bool = True

    @field_validator("sku", "name", "category", "unit")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El valor no puede estar vacío")
        return value

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value: str) -> str:
        return value.upper()

    @field_validator("description")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    unit: str | None = Field(default=None, min_length=1, max_length=30)
    minimum_stock: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=3)
    is_active: bool | None = None

    @field_validator("sku", "name", "category", "unit")
    @classmethod
    def normalize_required_text(cls, value: str | None, info) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("El valor no puede estar vacío")
        return value.upper() if info.field_name == "sku" else value

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class ProductRead(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LocationBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El nombre no puede estar vacío")
        return value

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class LocationCreate(LocationBase):
    pass


class LocationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("El nombre no puede estar vacío")
        return value

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class LocationRead(LocationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MovementCreate(BaseModel):
    movement_type: MovementType
    product_id: int = Field(gt=0)
    quantity: Decimal = Field(max_digits=14, decimal_places=3)
    source_location_id: int | None = Field(default=None, gt=0)
    destination_location_id: int | None = Field(default=None, gt=0)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @model_validator(mode="after")
    def validate_movement_shape(self) -> "MovementCreate":
        if self.quantity == 0:
            raise ValueError("La cantidad no puede ser cero")
        if self.movement_type != MovementType.ADJUSTMENT and self.quantity < 0:
            raise ValueError("La cantidad debe ser positiva")
        if self.movement_type == MovementType.ENTRY:
            if not self.destination_location_id or self.source_location_id:
                raise ValueError("Una entrada requiere solo una ubicación de destino")
        elif self.movement_type == MovementType.EXIT:
            if not self.source_location_id or self.destination_location_id:
                raise ValueError("Una salida requiere solo una ubicación de origen")
        elif self.movement_type == MovementType.TRANSFER:
            if not self.source_location_id or not self.destination_location_id:
                raise ValueError("Una transferencia requiere origen y destino")
            if self.source_location_id == self.destination_location_id:
                raise ValueError("El origen y el destino deben ser diferentes")
        elif self.movement_type == MovementType.ADJUSTMENT:
            if not self.destination_location_id or self.source_location_id:
                raise ValueError("Un ajuste requiere una ubicación")
        return self


class MovementRead(BaseModel):
    id: int
    movement_type: MovementType
    timestamp: datetime
    quantity: Decimal
    product_id: int
    product_sku: str
    product_name: str
    source_location_id: int | None
    source_location_name: str | None
    destination_location_id: int | None
    destination_location_name: str | None
    notes: str | None


class InventoryRead(BaseModel):
    id: int
    product_id: int
    product_sku: str
    product_name: str
    unit: str
    minimum_stock: Decimal
    location_id: int
    location_name: str
    quantity: Decimal
    is_below_minimum: bool
    updated_at: datetime


class LowStockProduct(BaseModel):
    product_id: int
    sku: str
    name: str
    unit: str
    minimum_stock: Decimal
    total_quantity: Decimal


class LocationStockSummary(BaseModel):
    location_id: int
    location_name: str
    total_quantity: Decimal


class DashboardRead(BaseModel):
    active_products: int
    total_inventory_units: Decimal
    low_stock_count: int
    low_stock_products: list[LowStockProduct]
    recent_movements: list[MovementRead]
    stock_by_location: list[LocationStockSummary]
