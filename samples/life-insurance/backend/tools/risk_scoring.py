"""Risk scoring domain logic — deterministic weighted scoring formula."""

RISK_CLASSES = [
    (90, "preferred_plus", "基準費率"),
    (75, "preferred", "+0~10%"),
    (60, "standard_plus", "+10~25%"),
    (40, "standard", "+25~50%"),
    (20, "substandard", "+50~150%"),
    (0, "decline", "N/A"),
]


def _score_age(age: int) -> tuple[int, str]:
    if age <= 35: return 95, "18-35歲，低風險"
    if age <= 50: return 65, "36-50歲，中風險"
    if age <= 65: return 35, "51-65歲，高風險"
    return 15, "65歲以上，極高風險"


def _score_bmi(bmi: float) -> tuple[int, str]:
    if 18 <= bmi < 25: return 95, f"BMI {bmi:.1f}，優良"
    if 25 <= bmi < 30: return 75, f"BMI {bmi:.1f}，標準"
    if 30 <= bmi < 35: return 45, f"BMI {bmi:.1f}，次標準"
    return 20, f"BMI {bmi:.1f}，高風險"


def _score_occupation(cls: int) -> tuple[int, str]:
    if cls <= 2: return 95, f"第{cls}類，低風險"
    if cls <= 4: return 60, f"第{cls}類，中風險"
    return 25, f"第{cls}類，高風險"


def _score_smoking(status: str) -> tuple[int, str]:
    m = {"never": (100, "非吸菸者"), "quit_over_1y": (70, "已戒菸超過1年"),
         "quit_under_1y": (40, "戒菸未滿1年"), "current": (20, "吸菸中")}
    return m.get(status, (70, status))


def _score_conditions(conditions: list[str]) -> tuple[int, str]:
    if not conditions or conditions == ["none"]:
        return 100, "無既往症"
    severe = [c for c in conditions if c in ("heart_disease", "cancer_active", "kidney_disease")]
    if severe:
        return 15, f"重大疾病：{', '.join(severe)}"
    controlled = [c for c in conditions if "controlled" in c]
    if controlled:
        return 45, f"慢性病控制中：{', '.join(controlled)}"
    return 30, f"既往症：{', '.join(conditions)}"


def _score_family(history: list[str]) -> tuple[int, str]:
    if not history or history == ["none"]:
        return 100, "無相關家族病史"
    before_60 = [h for h in history if "before_60" in h]
    if before_60:
        return 35, f"60歲前發病：{', '.join(before_60)}"
    return 70, f"家族病史：{', '.join(history)}"


def _level(score: int) -> str:
    if score >= 90: return "excellent"
    if score >= 75: return "low"
    if score >= 60: return "standard"
    if score >= 40: return "medium"
    if score >= 20: return "substandard"
    return "high"


def assess(age: int = 30, height_cm: float = 170, weight_kg: float = 65,
           occupation_class: int = 1, smoking_status: str = "never",
           conditions: list[str] | None = None, family_history: list[str] | None = None) -> dict:
    """Calculate risk score using weighted formula. Returns structured assessment."""
    conditions = conditions or ["none"]
    family_history = family_history or ["none"]
    bmi = weight_kg / (height_cm / 100) ** 2

    raw = [
        ("age", 0.20, *_score_age(age)),
        ("bmi", 0.20, *_score_bmi(bmi)),
        ("occupation", 0.15, *_score_occupation(occupation_class)),
        ("smoking", 0.15, *_score_smoking(smoking_status)),
        ("conditions", 0.20, *_score_conditions(conditions)),
        ("family_history", 0.10, *_score_family(family_history)),
    ]

    factors = []
    total = 0.0
    for name, weight, score, detail in raw:
        total += score * weight
        factors.append({"name": name, "score": score, "weight": weight, "level": _level(score), "detail": detail})

    final_score = int(total)
    risk_class, premium_impact = "decline", "N/A"
    for threshold, cls, impact in RISK_CLASSES:
        if final_score >= threshold:
            risk_class, premium_impact = cls, impact
            break

    return {
        "score": final_score, "risk_class": risk_class, "bmi": round(bmi, 1),
        "factors": factors, "premium_impact": premium_impact,
    }
