from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "services" / "api"
sys.path.insert(0, str(API_ROOT))

from app.db.session import SessionFactory  # noqa: E402
from app.models.product import Product  # noqa: E402
from app.repositories.products import ProductRepository  # noqa: E402


def main() -> None:
    catalog_path = REPO_ROOT / "data" / "catalog" / "demo_products.json"
    products = json.loads(catalog_path.read_text(encoding="utf-8"))
    repository = ProductRepository()

    created = 0
    skipped = 0
    with SessionFactory() as db:
        for item in products:
            existing = repository.get_by_sku(db, item["sku"])
            if existing is None and item.get("barcode"):
                existing = repository.get_by_barcode(db, item["barcode"])
            if existing is not None:
                skipped += 1
                continue
            repository.add(db, Product(**item, metadata_json={"catalog": "demo-v1"}))
            created += 1
        db.commit()

    print(f"Demo catalog seeded. created={created} skipped={skipped}")


if __name__ == "__main__":
    main()
