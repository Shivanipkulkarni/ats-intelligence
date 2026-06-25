from app.services.career_trajectory.extractor import seniority_rank, parse_roles_from_text

INDUSTRY_AVG_PROMOTION_MONTHS = 30


def compute_counterfactual(resume_text: str, roles: list | None = None) -> dict:
    if not roles:
        roles = parse_roles_from_text(resume_text)

    role_dicts = [r.model_dump() if hasattr(r, "model_dump") else r for r in roles]

    if len(role_dicts) < 2:
        return {
            "counterfactual_score": 60.0,
            "confidence": "Low",
            "reasons": ["Single role detected — insufficient data for counterfactual projection."],
        }

    total_beats = 0
    total_projections = 0

    current_rank = seniority_rank(role_dicts[0]["title"])
    cumulative_months = 0

    actual_ranks = [seniority_rank(r["title"]) for r in role_dicts]

    for i in range(len(role_dicts)):
        role = role_dicts[i]
        actual_rank = actual_ranks[i]
        duration = role.get("duration_months", 12)

        expected_rank_at_start = actual_ranks[0]
        expected_rank_now = expected_rank_at_start + int(cumulative_months / INDUSTRY_AVG_PROMOTION_MONTHS)

        actual_current = actual_rank
        deviation = actual_current - expected_rank_now

        total_beats += deviation
        total_projections += 1

        cumulative_months += duration

    if total_projections == 0:
        return {
            "counterfactual_score": 50.0,
            "confidence": "Low",
            "reasons": ["Unable to compute trajectory projections."],
        }

    avg_beat = total_beats / total_projections

    normalized_score = 50.0 + (avg_beat * 10.0)
    counterfactual_score = round(max(0, min(100, normalized_score)), 2)

    reasons = []
    if avg_beat > 0.5:
        reasons.append(f"Career consistently outpaces counterfactual (+{avg_beat:.1f} avg seniority beats) — high hidden potential signal.")
    elif avg_beat > -0.5:
        reasons.append("Career on par with counterfactual projection — expected trajectory.")
    else:
        reasons.append(f"Career lags counterfactual ({avg_beat:.1f} avg beats) — may be undervalued or in slower-moving industry.")

    confidence = "High" if total_projections >= 3 else "Medium" if total_projections >= 2 else "Low"

    return {
        "counterfactual_score": counterfactual_score,
        "confidence": confidence,
        "avg_seniority_beat": round(avg_beat, 2),
        "projections_analyzed": total_projections,
        "reasons": reasons,
    }
