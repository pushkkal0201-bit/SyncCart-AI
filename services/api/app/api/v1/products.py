from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import Envelope
from app.schemas.product import ProductCreate, ProductRead
from app.services.products import ProductService

router = APIRouter()
service = ProductService()


@router.get("", response_model=Envelope[list[ProductRead]])
def list_products(
    request: Request, db: Annotated[Session, Depends(get_db)]
) -> Envelope[list[ProductRead]]:
    products = service.list(db)
    return Envelope(
        data=[ProductRead.model_validate(p) for p in products],
        meta={"request_id": request.state.request_id},
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Envelope[ProductRead])
def create_product(
    payload: ProductCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> Envelope[ProductRead]:
    product = service.create(db, payload)
    return Envelope(
        data=ProductRead.model_validate(product),
        meta={"request_id": request.state.request_id},
    )


@router.get("/barcode/{barcode}", response_model=Envelope[ProductRead])
def get_product_by_barcode(
    barcode: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> Envelope[ProductRead]:
    product = service.get_by_barcode(db, barcode)
    return Envelope(
        data=ProductRead.model_validate(product),
        meta={"request_id": request.state.request_id},
    )


@router.get("/{sku}", response_model=Envelope[ProductRead])
def get_product(
    sku: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> Envelope[ProductRead]:
    product = service.get_by_sku(db, sku)
    return Envelope(
        data=ProductRead.model_validate(product),
        meta={"request_id": request.state.request_id},
    )
