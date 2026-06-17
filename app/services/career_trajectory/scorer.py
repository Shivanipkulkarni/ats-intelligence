from app.services.career_trajectory.extractor import parse_roles_from_text
from app.services.career_trajectory.analyzer import (
    analyze_promotions,
    analyze_leadership,
    analyze_ownership,
    analyze_technical_progression,
    analyze_tenure,
    analyze_role_transitions,
)

DIMENSION_WEIGHTS = {
    "promotions": 0.25,
    "leadership": 0.20,
    "ownership": 0.20,
    "technical_progression": 0.15,
    "tenure": 0.10,
    "role_transitions": 0.10,
}

def _trajectory_label(score: float) -> str:
    if score >= 78:
        return "Accelerating"
    elif score >= 55:
        return "Steady"
    return "Plateaued"

def _confidence(num_roles: int) -> str:
    if num_roles >= 3:
        return "High"
    elif num_roles == 2:
        return "Medium"
    return "Low"

def _generate_reasons(dim_scores: dict, label: str) -> list[str]:
    reasons = []

    if label == "Accelerating":
        reasons.append("Career shows continuous upward trajectory.")
    elif label == "Steady":
        reasons.append("Stable career progression with consistent growth.")
    else:
        reasons.append("Career appears to have plateaued — limited upward movement detected.")

    if dim_scores["promotions"]["score"] >= 75:
        reasons.append("Clear seniority progression across roles.")

    if dim_scores["leadership"]["score"] >= 70:
        reasons.append("Strong leadership signals in recent roles.")

    if dim_scores["ownership"]["score"] >= 70:
        reasons.append("Demonstrates end-to-end ownership and initiative.")

    if dim_scores["tenure"]["score"] < 50:
        reasons.append("Short tenures detected — may indicate instability or contract roles.")

    if dim_scores["role_transitions"]["score"] >= 85:
        reasons.append("Intentional cross-functional pivots show breadth.")

    return reasons

def compute_career_trajectory(resume_text: str, roles: list | None = None) -> dict:
    if not roles:
        roles = parse_roles_from_text(resume_text)

    # Convert Pydantic models to dicts if needed
    role_dicts = [r.model_dump() if hasattr(r, "model_dump") else r for r in roles]

    dim_scores = {
        "promotions": analyze_promotions(role_dicts),
        "leadership": analyze_leadership(role_dicts),
        "ownership": analyze_ownership(role_dicts),
        "technical_progression": analyze_technical_progression(role_dicts),
        "tenure": analyze_tenure(role_dicts),
        "role_transitions": analyze_role_transitions(role_dicts),
    }

    weighted_score = sum(
        dim_scores[dim]["score"] * weight
        for dim, weight in DIMENSION_WEIGHTS.items()
    )
    final_score = round(weighted_score, 2)
    label = _trajectory_label(final_score)

    return {
        "career_growth_score": final_score,
        "confidence": _confidence(len(role_dicts)),
        "dimension_scores": {k: round(v["score"], 2) for k, v in dim_scores.items()},
        "trajectory_label": label,
        "reasons": _generate_reasons(dim_scores, label),
    }