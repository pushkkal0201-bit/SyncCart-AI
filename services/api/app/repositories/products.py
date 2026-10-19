from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.product import Product


class ProductRepository:
    def list(self, db: Session) -> list[Product]:
        return list(db.scalars(select(Product).order_by(Product.name.asc())).all())

    def get_by_sku(self, db: Session, sku: str) -> Product | None:
        return db.scalar(select(Product).where(Product.sku == sku))

    def get_by_barcode(self, db: Session, barcode: str) -> Product | None:
        return db.scalar(select(Product).where(Product.barcode == barcode))

    def conflict_exists(self, db: Session, *, sku: str, barcode: str | None) -> bool:
        clauses = [Product.sku == sku]
        if barcode:
            clauses.append(Product.barcode == barcode)
        return db.scalar(select(Product.id).where(or_(*clauses)).limit(1)) is not None

    def add(self, db: Session, product: Product) -> Product:
        db.add(product)
        db.flush()
        return product
