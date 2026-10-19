from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import ProductConflict, ProductNotFound
from app.models.product import Product
from app.repositories.products import ProductRepository
from app.schemas.product import ProductCreate


class ProductService:
    def __init__(self, repository: ProductRepository | None = None) -> None:
        self.repository = repository or ProductRepository()

    def list(self, db: Session) -> list[Product]:
        return self.repository.list(db)

    def get_by_sku(self, db: Session, sku: str) -> Product:
        product = self.repository.get_by_sku(db, sku.strip().upper())
        if product is None:
            raise ProductNotFound(f"Product with SKU '{sku}' was not found")
        return product

    def get_by_barcode(self, db: Session, barcode: str) -> Product:
        normalized = barcode.strip().upper()
        product = self.repository.get_by_barcode(db, normalized)
        if product is None:
            raise ProductNotFound(f"No product is registered for barcode '{barcode}'")
        return product

    def create(self, db: Session, data: ProductCreate) -> Product:
        if self.repository.conflict_exists(db, sku=data.sku, barcode=data.barcode):
            raise ProductConflict("A product with this SKU or barcode already exists")
        product = Product(**data.model_dump())
        self.repository.add(db, product)
        db.commit()
        db.refresh(product)
        return product
