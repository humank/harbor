"""Premium calculation domain logic — deterministic formula."""

from backend.tools.product_search import load_products

RISK_MULTIPLIER = {
    "preferred_plus": 0.85, "preferred": 0.95, "standard_plus": 1.05,
    "standard": 1.20, "substandard": 1.60, "decline": 2.00,
}

AGE_FACTOR = {(0, 25): 0.80, (26, 35): 1.00, (36, 45): 1.25, (46, 55): 1.55, (56, 65): 2.00, (66, 100): 2.50}


def _age_factor(age: int) -> float:
    for (lo, hi), factor in AGE_FACTOR.items():
        if lo <= age <= hi:
            return factor
    return 1.0


def calc_batch(items: list[dict]) -> dict:
    """Calculate premiums for a list of {product_id, age, risk_class}."""
    products = {p["product_id"]: p for p in load_products()}
    results = []
    for item in items:
        product = products.get(item.get("product_id", ""))
        if not product:
            continue
        base = product["base_premium_monthly"]
        risk_mult = RISK_MULTIPLIER.get(item.get("risk_class", "standard"), 1.0)
        age_mult = _age_factor(item.get("age", 30))
        monthly = int(base * risk_mult * age_mult)
        results.append({
            "product_id": product["product_id"], "product_name": product["name"],
            "annual_premium": monthly * 12, "monthly_premium": monthly,
            "risk_adjustment": round(risk_mult * age_mult, 2),
            "breakdown": {"base": base, "risk_loading": max(0, monthly - base), "discount": 0},
        })
    return {"results": results, "total_monthly": sum(r["monthly_premium"] for r in results),
            "total_annual": sum(r["annual_premium"] for r in results)}
