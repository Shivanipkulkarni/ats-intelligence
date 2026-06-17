from app.services.semantic_fit.scorer import compute_semantic_fit
from app.services.career_trajectory.scorer import compute_career_trajectory
from app.services.company_context.scorer import compute_company_context

# Default weights — tunable per role type via API
DEFAULT_WEIGHTS = {
    "semantic_fit":    0.40,
    "career_growth":   0.35,
    "company_context": 0.25,
}

def _validate_weights(weights: dict) -> dict:
    """Ensure weights sum to 1.0. Falls back to default if invalid."""
    keys = {"semantic_fit", "career_growth", "company_context"}
    if not weights or set(weights.keys()) != keys:
        return DEFAULT_WEIGHTS
    total = sum(weights.values())
    if abs(total - 1.0) > 0.01:
        # Normalize
        return {k: round(v / total, 4) for k, v in weights.items()}
    return weights

def _grade(score: float) -> str:
    if score >= 85: return "A"
    if score >= 70: return "B"
    if score >= 55: return "C"
    return "D"

def _verdict(score: float, flags: list[str]) -> str:
    if score >= 85:
        return "Strong Hidden Talent — Highly Recommended for Review"
    elif score >= 70:
        return "Likely Hidden Talent — Recommended for Review"
    elif score >= 55:
        return "Potential Fit — Manual Review Suggested"
    else:
        return "Low Signal — May Not Be the Right Fit"

def _collect_flags(semantic: dict, career: dict, company: dict) -> list[str]:
    flags = []
    if semantic["confidence"] == "Low":
        flags.append("Low confidence on semantic match — resume may be too short.")
    if career["confidence"] == "Low":
        flags.append("Low confidence on career data — only one role detected.")
    if company["confidence"] == "Low":
        flags.append("No structured company data — company context score is estimated.")
    if career["trajectory_label"] == "Plateaued":
        flags.append("Career trajectory shows limited growth in recent roles.")
    if company["scope_multiplier"] < 0.95:
        flags.append("Enterprise background — scope may be narrower than title suggests.")
    return flags

def _pick_top_reasons(semantic: dict, career: dict, company: dict, n: int = 5) -> list[str]:
    """
    Pull the most meaningful reasons across all three modules.
    Prioritize by module weight: semantic > career > company.
    """
    all_reasons = (
        semantic["reasons"][:2] +
        career["reasons"][:2] +
        company["reasons"][:2]
    )
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for r in all_reasons:
        if r not in seen:
            seen.add(r)
            unique.append(r)
    return unique[:n]

def compute_core_score(
    resume_text: str,
    job_description: str,
    roles: list | None = None,
    companies: list | None = None,
    weights: dict | None = None,
) -> dict:

    weights = _validate_weights(weights or {})

    # --- Run all three modules ---
    semantic  = compute_semantic_fit(resume_text, job_description)
    career    = compute_career_trajectory(resume_text, roles)
    company   = compute_company_context(resume_text, companies)

    # --- Weighted aggregation ---
    overall = round(
        semantic["semantic_fit_score"]      * weights["semantic_fit"] +
        career["career_growth_score"]       * weights["career_growth"] +
        company["company_context_score"]    * weights["company_context"],
        2
    )

    flags   = _collect_flags(semantic, career, company)
    grade   = _grade(overall)
    verdict = _verdict(overall, flags)

    return {
        "overall_hidden_talent_score": overall,
        "grade": grade,
        "verdict": verdict,
        "semantic_fit": {
            "score":      semantic["semantic_fit_score"],
            "confidence": semantic["confidence"],
            "reasons":    semantic["reasons"],
        },
        "career_growth": {
            "score":      career["career_growth_score"],
            "confidence": career["confidence"],
            "reasons":    career["reasons"],
        },
        "company_context": {
            "score":      company["company_context_score"],
            "confidence": company["confidence"],
            "reasons":    company["reasons"],
        },
        "weights_used":  weights,
        "top_reasons":   _pick_top_reasons(semantic, career, company),
        "flags":         flags,
    }