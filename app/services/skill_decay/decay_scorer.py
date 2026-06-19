from app.services.skill_decay.skill_extractor import map_skills_to_roles, get_decay_speed

DECAY_RATES = {
    "fast":   3.0,
    "medium": 1.8,
    "slow":   1.0,
}


def _categorize(freshness: float) -> str:
    if freshness >= 85:
        return "Current"
    elif freshness >= 60:
        return "Recent"
    elif freshness >= 35:
        return "Aging"
    return "Stale"


def _freshness_score(months_ago: int, decay_speed: str) -> float:
    rate = DECAY_RATES[decay_speed]
    score = 100.0 - (months_ago * rate)
    return round(max(score, 0.0), 2)


def _confidence(num_roles: int, num_skills: int) -> str:
    if num_roles >= 3 and num_skills >= 5:
        return "High"
    elif num_roles >= 2 and num_skills >= 3:
        return "Medium"
    return "Low"


def _generate_reasons(breakdown: list[dict], overall_score: float) -> list[str]:
    reasons = []

    stale = [b for b in breakdown if b["decay_category"] == "Stale"]
    current = [b for b in breakdown if b["decay_category"] == "Current"]

    if overall_score >= 75:
        reasons.append("Most listed skills are actively used in recent roles.")
    elif overall_score >= 50:
        reasons.append("Skill set shows a healthy mix of current and aging skills.")
    else:
        reasons.append("Several key skills appear outdated based on role history.")

    if current:
        skill_names = ", ".join(s["skill"] for s in current[:3])
        reasons.append(f"Actively current skills: {skill_names}.")

    if stale:
        skill_names = ", ".join(s["skill"] for s in stale[:3])
        reasons.append(f"Potentially outdated: {skill_names} — verify recency in interview.")

    return reasons


def compute_skill_decay(resume_text: str, roles: list | None = None) -> dict:
    if not roles:
        return {
            "skill_currency_score": 60.0,
            "confidence": "Low",
            "skill_breakdown": [],
            "reasons": [
                "No structured role history provided.",
                "Pass roles list for accurate skill decay analysis.",
                "Default neutral score applied.",
            ],
        }

    role_dicts = [r.model_dump() if hasattr(r, "model_dump") else r for r in roles]
    skill_map = map_skills_to_roles(role_dicts)

    if not skill_map:
        return {
            "skill_currency_score": 60.0,
            "confidence": "Low",
            "skill_breakdown": [],
            "reasons": ["No recognizable technical skills found in role responsibilities."],
        }

    breakdown = []
    for skill, info in skill_map.items():
        decay_speed = get_decay_speed(skill)
        freshness = _freshness_score(info["months_ago"], decay_speed)
        breakdown.append({
            "skill": skill,
            "last_used_role": info["role_title"],
            "months_since_used": info["months_ago"],
            "freshness_score": freshness,
            "decay_category": _categorize(freshness),
        })

    breakdown.sort(key=lambda x: x["freshness_score"], reverse=True)

    overall_score = round(sum(b["freshness_score"] for b in breakdown) / len(breakdown), 2)

    return {
        "skill_currency_score": overall_score,
        "confidence": _confidence(len(role_dicts), len(breakdown)),
        "skill_breakdown": breakdown,
        "reasons": _generate_reasons(breakdown, overall_score),
    }