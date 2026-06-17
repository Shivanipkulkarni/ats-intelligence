from app.services.semantic_fit.preprocessor import extract_sections
from app.services.semantic_fit.similarity import compute_section_similarities

# Section weights — tune these based on role type in future
SECTION_WEIGHTS = {
    "skills": 0.35,
    "experience": 0.35,
    "projects": 0.15,
    "education": 0.10,
    "general": 0.05,
}
DEFAULT_WEIGHT = 0.10  # for any unrecognized section (excluding 'full')

def _normalize_score(cosine: float) -> float:
    """
    Map cosine similarity [-1, 1] → percentage [0, 100].
    In practice resume/JD similarity is always positive (0.2–0.95).
    We rescale [0.2, 0.95] → [0, 100] for better spread.
    """
    clipped = max(0.2, min(0.95, cosine))
    return round(((clipped - 0.2) / 0.75) * 100, 2)

def _confidence_label(score: float) -> str:
    if score >= 75:
        return "High"
    elif score >= 50:
        return "Medium"
    return "Low"

def _generate_reasons(section_scores: dict[str, float], final_score: float) -> list[str]:
    reasons = []

    if final_score >= 75:
        reasons.append("Strong semantic alignment despite possible keyword differences.")
    elif final_score >= 50:
        reasons.append("Moderate semantic match — candidate may use different terminology.")
    else:
        reasons.append("Low semantic alignment — role requirements may differ significantly.")

    skills_score = section_scores.get("skills", None)
    if skills_score is not None:
        if _normalize_score(skills_score) >= 70:
            reasons.append("Skill section closely aligns with job requirements semantically.")
        else:
            reasons.append("Skill terminology differs — manual review recommended.")

    exp_score = section_scores.get("experience", None)
    if exp_score is not None and _normalize_score(exp_score) >= 70:
        reasons.append("Work experience context matches job description well.")

    return reasons

def compute_semantic_fit(resume_text: str, job_description: str) -> dict:
    resume_sections = extract_sections(resume_text)
    jd_sections = extract_sections(job_description)

    raw_section_scores = compute_section_similarities(resume_sections, jd_sections)

    # Weighted average (exclude 'full' from weighted calc — used only for fallback)
    weighted_sum = 0.0
    weight_total = 0.0
    normalized_sections = {}

    for section, raw_score in raw_section_scores.items():
        if section == "full":
            continue
        norm = _normalize_score(raw_score)
        normalized_sections[section] = norm
        w = SECTION_WEIGHTS.get(section, DEFAULT_WEIGHT)
        weighted_sum += norm * w
        weight_total += w

    # If no named sections found, fall back to full-text score
    if weight_total == 0:
        full_raw = raw_section_scores.get("full", 0.0)
        final_score = _normalize_score(full_raw)
        normalized_sections["full"] = final_score
    else:
        final_score = round(weighted_sum / weight_total, 2)

    raw_cosine = raw_section_scores.get("full", 0.0)

    return {
        "semantic_fit_score": final_score,
        "cosine_similarity": round(raw_cosine, 4),
        "confidence": _confidence_label(final_score),
        "reasons": _generate_reasons(raw_section_scores, final_score),
        "section_scores": normalized_sections,
    }