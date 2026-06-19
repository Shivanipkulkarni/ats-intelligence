from app.services.crisis_response.gap_detector import (
    detect_gaps, find_recovery_signals,
    MINOR_GAP_THRESHOLD, SIGNIFICANT_GAP_THRESHOLD,
)


def _classify_gap(months: int, recovery_signals: list[str]) -> str:
    if months < MINOR_GAP_THRESHOLD:
        return "Minor"
    if recovery_signals:
        return "Adaptive"
    return "Unexplained"


def _confidence(num_roles: int) -> str:
    if num_roles >= 3:
        return "High"
    elif num_roles == 2:
        return "Medium"
    return "Low"


def _generate_reasons(gap_results: list[dict], resilience_score: float) -> list[str]:
    reasons = []

    adaptive = [g for g in gap_results if g["classification"] == "Adaptive"]
    unexplained = [g for g in gap_results if g["classification"] == "Unexplained"]

    if not gap_results:
        reasons.append("No significant employment gaps detected — consistent work history.")
    elif resilience_score >= 75:
        reasons.append("Career shows productive activity even through transitions.")
    elif resilience_score >= 50:
        reasons.append("Some gaps present, with partial evidence of productive activity.")
    else:
        reasons.append("Gaps detected with no clear evidence of activity — worth asking about directly.")

    if adaptive:
        reasons.append(f"{len(adaptive)} gap(s) show recovery signals (freelancing, projects, certifications).")

    if unexplained:
        reasons.append(f"{len(unexplained)} gap(s) have no explanation in the resume — clarify in interview, not a disqualifier.")

    return reasons


def compute_crisis_response(resume_text: str, roles: list | None = None) -> dict:
    if not roles:
        return {
            "resilience_score": 65.0,
            "confidence": "Low",
            "gaps_detected": [],
            "reasons": [
                "No structured role history provided.",
                "Pass roles list for accurate gap and resilience analysis.",
                "Default neutral score applied.",
            ],
        }

    role_dicts = [r.model_dump() if hasattr(r, "model_dump") else r for r in roles]
    raw_gaps = detect_gaps(role_dicts)

    if not raw_gaps:
        return {
            "resilience_score": 85.0,
            "confidence": _confidence(len(role_dicts)),
            "gaps_detected": [],
            "reasons": ["No significant employment gaps detected — consistent work history."],
        }

    gap_results = []
    for gap in raw_gaps:
        # Also scan overall resume text in case recovery signals are
        # mentioned outside the specific role's bullet points
        combined_text = gap["role_text"] + " " + resume_text
        signals = find_recovery_signals(combined_text)
        classification = _classify_gap(gap["estimated_months"], signals)

        gap_results.append({
            "gap_position": gap["position"],
            "gap_months": gap["estimated_months"],
            "recovery_signals_found": signals,
            "classification": classification,
        })

    # Score: Minor gaps don't hurt, Adaptive gaps barely hurt,
    # Unexplained gaps reduce score most
    total = len(gap_results)
    score = 100.0
    for g in gap_results:
        if g["classification"] == "Adaptive":
            score -= 5
        elif g["classification"] == "Unexplained":
            score -= 15
        # "Minor" gaps: no penalty

    resilience_score = round(max(score, 0.0), 2)

    return {
        "resilience_score": resilience_score,
        "confidence": _confidence(len(role_dicts)),
        "gaps_detected": gap_results,
        "reasons": _generate_reasons(gap_results, resilience_score),
    }