"""Compliance check domain logic — deterministic rule engine."""

AGE_LIMITS = {
    "終身壽險": (0, 70), "定期壽險": (20, 65), "醫療險": (0, 70),
    "重大傷病": (0, 65), "意外險": (16, 65), "長照險": (20, 60),
    "年金險": (20, 70), "投資型": (20, 70),
}


def check(age: int = 30, product_category: str = "醫療險", sum_insured: int = 0,
           annual_income: int | None = None, annual_premium_total: int | None = None) -> dict:
    """Check compliance rules. Returns {eligible, checks, warnings}."""
    checks = []
    warnings: list[str] = []

    lo, hi = AGE_LIMITS.get(product_category, (0, 75))
    passed = lo <= age <= hi
    checks.append({"rule": "age_range", "passed": passed,
                    "detail": f"{age}歲{'在' if passed else '不在'}承保範圍 {lo}-{hi} 歲內"})

    needs_exam = sum_insured > 5_000_000
    checks.append({"rule": "medical_exam", "passed": not needs_exam,
                    "detail": "保額超過500萬需體檢" if needs_exam else "保額未超過免體檢額度"})
    if needs_exam:
        warnings.append("保額超過500萬，需安排體檢")

    if annual_income and annual_premium_total:
        ratio = annual_premium_total / annual_income
        passed = ratio <= 0.3
        checks.append({"rule": "financial_check", "passed": passed,
                        "detail": f"年繳保費佔年收入 {ratio:.1%}，{'未' if passed else '已'}超過 30%"})
        if not passed:
            warnings.append("年繳保費超過年收入30%，需提供財力證明")
    else:
        checks.append({"rule": "financial_check", "passed": True, "detail": "未提供收入資訊，跳過財力檢查"})

    if age < 15 and product_category in ("終身壽險", "定期壽險"):
        checks.append({"rule": "minor_restriction", "passed": False, "detail": "15歲以下不得有死亡給付"})
    else:
        checks.append({"rule": "minor_restriction", "passed": True,
                        "detail": "非未成年人，無限制" if age >= 18 else "未成年但無死亡給付限制"})

    return {"eligible": all(c["passed"] for c in checks), "checks": checks, "warnings": warnings}
