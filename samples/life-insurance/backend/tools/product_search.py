"""Product search domain logic — pure Python, no framework dependency."""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def load_products() -> list[dict]:
    products = []
    for f in ["products_cathay.json", "products_fubon.json"]:
        products.extend(json.loads((DATA_DIR / f).read_text()))
    return products


def search(age: int = 0, types: list[str] | None = None, budget_monthly: int = 0,
           providers: list[str] | None = None) -> dict:
    """Filter products by age, category types, budget, and provider."""
    providers = providers or ["cathay", "fubon"]
    types_lower = [t.lower() for t in (types or [])]
    results = []
    for p in load_products():
        if p["provider"] not in providers:
            continue
        if age and not (p["age_range"]["min"] <= age <= p["age_range"]["max"]):
            continue
        if types_lower and not any(t in p["category"].lower() for t in types_lower):
            continue
        if budget_monthly and p["base_premium_monthly"] > budget_monthly:
            continue
        results.append(p)
    return {"products": results, "total": len(results)}


def compare(product_ids: list[str]) -> dict:
    """Compare specific products by ID."""
    all_products = {p["product_id"]: p for p in load_products()}
    matched = [all_products[pid] for pid in product_ids if pid in all_products]
    return {"products": matched, "total": len(matched)}
