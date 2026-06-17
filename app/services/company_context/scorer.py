from app.services.company_context.classifier import classify_company
from app.services.company_context.scope_analyzer import analyze_scope

def _confidence(num_companies: int) -> str:
    if num_companies >= 3:
        return "High"
    elif num_companies == 2:
        return "Medium"
    return "Low"

def _generate_reasons(per_company: list[dict], final_score: float, avg_multiplier: float) -> list[str]:
    reasons = []

    if avg_multiplier > 1.15:
        reasons.append("Worked in startups requiring cross-functional ownership — responsibilities normalized upward.")
    elif avg_multiplier < 0.95:
        reasons.append("Enterprise background — scope may be narrower than title suggests.")
    else:
        reasons.append("Mixed or mid-stage company background — standard scope assumed.")

    for c in per_company:
        if c["scope_score"] >= 70:
            reasons.append(f"Broad scope at {c['company_name']} ({c['stage']}, {c['size_bucket']} size).")
        if c["scope_multiplier"] >= 1.3:
            reasons.append(f"{c['company_name']} is a micro/small startup — title likely understates seniority.")

    if final_score >= 78:
        reasons.append("Company context strongly favors this candidate's hidden seniority.")

    return reasons

def compute_company_context(resume_text: str, companies: list | None = None) -> dict:
    if not companies:
        # Fallback: no structured input → return neutral score with explanation
        return {
            "company_context_score": 65.0,
            "confidence": "Low",
            "per_company_scores": [],
            "scope_multiplier": 1.0,
            "reasons": [
                "No structured company data provided.",
                "Pass company entries for accurate context normalization.",
                "Default neutral score applied."
            ],
        }

    company_dicts = [
        c.model_dump() if hasattr(c, "model_dump") else c
        for c in companies
    ]

    per_company_scores = []
    multipliers = []

    for c in company_dicts:
        classification = classify_company(
            company_name=c["company_name"],
            employee_count=c.get("employee_count"),
            funding_stage=c.get("funding_stage"),
            responsibilities=c.get("responsibilities", []),
        )

        scope = analyze_scope(
            responsibilities=c.get("responsibilities", []),
            role_title=c.get("role_title", ""),
        )

        # Raw score = scope score × scope multiplier (capped at 100)
        raw_score = min(scope["scope_score"] * classification["scope_multiplier"], 100.0)

        per_company_scores.append({
            "company_name": c["company_name"],
            "role_title": c.get("role_title", ""),
            "stage": classification["stage"],
            "size_bucket": classification["size_bucket"],
            "scope_multiplier": classification["scope_multiplier"],
            "scope_score": scope["scope_score"],
            "normalized_score": round(raw_score, 2),
            "breadth_signals": scope["breadth_signals"],
        })
        multipliers.append(classification["scope_multiplier"])

    # Weight recent companies more (last = highest weight)
    n = len(per_company_scores)
    weights = [1 + i for i in range(n)]           # [1, 2, 3, ...]
    weighted_score = sum(
        per_company_scores[i]["normalized_score"] * weights[i]
        for i in range(n)
    ) / sum(weights)

    avg_multiplier = round(sum(multipliers) / len(multipliers), 3)
    final_score = round(weighted_score, 2)

    return {
        "company_context_score": final_score,
        "confidence": _confidence(n),
        "per_company_scores": per_company_scores,
        "scope_multiplier": avg_multiplier,
        "reasons": _generate_reasons(per_company_scores, final_score, avg_multiplier),
    }