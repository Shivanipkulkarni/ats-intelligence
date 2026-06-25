import re
import numpy as np


SKILL_KEYWORDS = [
    "python", "java", "javascript", "typescript", "go", "rust", "c++", "c#",
    "react", "angular", "vue", "node", "django", "fastapi", "flask", "spring",
    "aws", "gcp", "azure", "kubernetes", "docker", "terraform", "jenkins",
    "sql", "postgres", "mysql", "mongodb", "redis", "kafka", "spark", "hadoop",
    "machine learning", "deep learning", "llm", "nlp", "pytorch", "tensorflow",
    "git", "ci/cd", "rest", "graphql", "microservices", "agile", "scrum",
    "html", "css", "sass", "webpack", "figma", "tableau", "power bi", "excel",
]

EXPERIENCE_YEAR_SIGNALS = [
    r"(\d+)\+?\s*(?:years?|yrs?).*(?:experience|exp)",
    r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp)",
]


def compute_keyword_match_resume_jd(resume_text: str, jd_text: str) -> dict:
    resume_lower = resume_text.lower()
    jd_lower = jd_text.lower()

    resume_words = set(re.findall(r"[a-z0-9+#]+", resume_lower))
    jd_words = set(re.findall(r"[a-z0-9+#]+", jd_lower))

    jd_skills_found = []
    for skill in SKILL_KEYWORDS:
        if skill in jd_lower:
            in_resume = skill in resume_lower
            jd_skills_found.append({
                "skill": skill,
                "in_jd": True,
                "in_resume": in_resume,
                "match": in_resume,
            })

    skills_in_jd = [s for s in jd_skills_found if s["in_jd"]]
    matched_skills = [s for s in skills_in_jd if s["match"]]
    skill_match_rate = round(len(matched_skills) / max(len(skills_in_jd), 1) * 100, 2)

    jd_bigrams = set()
    for i in range(len(jd_words) - 1):
        jd_bigrams.add(f"{list(jd_words)[i]} {list(jd_words)[i+1]}")

    resume_bigrams = set()
    rw_list = list(resume_words)
    for i in range(len(rw_list) - 1):
        resume_bigrams.add(f"{rw_list[i]} {rw_list[i+1]}")

    bigram_overlap = len(jd_bigrams & resume_bigrams) / max(len(jd_bigrams), 1) * 100

    jd_years_req = []
    for pattern in EXPERIENCE_YEAR_SIGNALS:
        for match in re.finditer(pattern, jd_lower):
            jd_years_req.append(int(match.group(1)))

    resume_years_mentioned = []
    for pattern in EXPERIENCE_YEAR_SIGNALS:
        for match in re.finditer(pattern, resume_lower):
            resume_years_mentioned.append(int(match.group(1)))

    avg_jd_years = np.mean(jd_years_req) if jd_years_req else 0
    avg_resume_years = np.mean(resume_years_mentioned) if resume_years_mentioned else 0

    years_match = 100.0
    if avg_jd_years > 0 and avg_resume_years > 0:
        ratio = avg_resume_years / avg_jd_years
        if ratio < 0.5:
            years_match = 30.0
        elif ratio < 0.8:
            years_match = 60.0
        elif ratio <= 1.5:
            years_match = 100.0
        else:
            years_match = 80.0

    term_overlap = len(resume_words & jd_words) / max(len(jd_words), 1) * 100

    keyword_score = round(
        skill_match_rate * 0.5 +
        bigram_overlap * 0.1 +
        term_overlap * 0.25 +
        years_match * 0.15,
        2
    )

    return {
        "keyword_match_score": keyword_score,
        "skill_match_rate": skill_match_rate,
        "skills_in_jd": len(skills_in_jd),
        "skills_matched": len(matched_skills),
        "term_overlap_pct": round(term_overlap, 2),
        "bigram_overlap_pct": round(bigram_overlap, 2),
        "years_experience_match": round(years_match, 2),
        "jd_years_required": round(avg_jd_years, 1),
        "resume_years_mentioned": round(avg_resume_years, 1),
        "skill_breakdown": jd_skills_found,
    }


def compute_bias_comparison(
    lsa_results: list[dict],
    keyword_results: list[dict],
    top_k: int = 100,
) -> dict:
    lsa_ranked_ids = [r["resume_id"] for r in lsa_results[:top_k]]
    kw_ranked_ids = [r["resume_id"] for r in keyword_results[:top_k]]

    lsa_set = set(lsa_ranked_ids)
    kw_set = set(kw_ranked_ids)

    overlap = lsa_set & kw_set
    lsa_only = lsa_set - kw_set
    kw_only = kw_set - lsa_set

    rank_diffs = {}
    for rid in overlap:
        lsa_pos = next(i for i, r in enumerate(lsa_results) if r["resume_id"] == rid)
        kw_pos = next(i for i, r in enumerate(keyword_results) if r["resume_id"] == rid)
        rank_diffs[rid] = kw_pos - lsa_pos

    avg_rank_shift = round(sum(rank_diffs.values()) / max(len(rank_diffs), 1), 2)

    summary = {
        "overlap_count": len(overlap),
        "overlap_pct": round(len(overlap) / top_k * 100, 1),
        "lsa_only_count": len(lsa_only),
        "keyword_only_count": len(kw_only),
        "avg_rank_shift": avg_rank_shift,
    }

    examples = {
        "lsa_only": list(lsa_only)[:5],
        "keyword_only": list(kw_only)[:5],
        "biggest_rank_swings": sorted(
            rank_diffs.items(), key=lambda x: abs(x[1]), reverse=True
        )[:5],
    }

    return {
        "summary": summary,
        "examples": examples,
    }
