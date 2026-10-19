from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.cart import CartItem, CartSource


class CartRepository:
    def list_items(self, db: Session, *, session_id: str, source: CartSource) -> list[CartItem]:
        statement = (
            select(CartItem)
            .options(joinedload(CartItem.product))
            .where(
                CartItem.session_id == session_id,
                CartItem.source == source.value,
                CartItem.quantity > 0,
            )
            .order_by(CartItem.updated_at.desc())
        )
        return list(db.scalars(statement).all())

    def get_item(
        self,
        db: Session,
        *,
        session_id: str,
        product_id: str,
        source: CartSource,
    ) -> CartItem | None:
        statement = select(CartItem).where(
            CartItem.session_id == session_id,
            CartItem.product_id == product_id,
            CartItem.source == source.value,
        )
        return db.scalar(statement)

    def add(self, db: Session, item: CartItem) -> CartItem:
        db.add(item)
        db.flush()
        return item
