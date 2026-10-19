from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import customer_actions, monitoring, products, reconciliation, sessions, simulator, store_ops, vision

api_router = APIRouter()
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(customer_actions.router, prefix="/sessions", tags=["customer-actions"])
api_router.include_router(reconciliation.router, prefix="/sessions", tags=["reconciliation"])
api_router.include_router(simulator.router, prefix="/simulator", tags=["simulator"])
api_router.include_router(store_ops.router, prefix="/store", tags=["store-operations"])
api_router.include_router(vision.router, prefix="/vision", tags=["vision-edge"])

api_router.include_router(monitoring.router, prefix="/admin", tags=["monitoring"])
