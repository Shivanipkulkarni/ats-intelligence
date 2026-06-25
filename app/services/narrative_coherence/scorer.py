import re
from app.services.career_trajectory.extractor import (
    seniority_rank, parse_roles_from_text,
    LEADERSHIP_SIGNALS, OWNERSHIP_SIGNALS,
)

TITLE_RESPONSIBILITY_MAP = {
    "senior": ["architect", "design", "lead", "mentor", "strategy", "roadmap"],
    "lead": ["architect", "strategy", "roadmap", "cross-team", "mentor", "design"],
    "junior": ["implement", "develop", "fix", "test", "learn", "assist"],
    "intern": ["learn", "assist", "support", "shadow", "document"],
}


def compute_narrative_coherence(resume_text: str, roles: list | None = None) -> dict:
    if not roles:
        roles = parse_roles_from_text(resume_text)
    if not roles or len(roles) < 2:
        return {
            "narrative_coherence_score": 60.0,
            "confidence": "Low",
            "reasons": ["Single role or no roles detected — insufficient narrative data."],
        }

    role_dicts = [r.model_dump() if hasattr(r, "model_dump") else r for r in roles]

    score = 60.0
    signals = []
    issues = []

    title_ranks = [seniority_rank(r["title"]) for r in role_dicts]

    upward_moves = sum(
        1 for i in range(1, len(title_ranks)) if title_ranks[i] > title_ranks[i - 1]
    )
    downward_moves = sum(
        1 for i in range(1, len(title_ranks)) if title_ranks[i] < title_ranks[i - 1]
    )

    if downward_moves == 0 and upward_moves > 0:
        score += 15
        signals.append("Clean upward seniority progression.")
    elif downward_moves > upward_moves:
        score -= 20
        issues.append("Multiple downward title moves without explanation.")

    for i, role in enumerate(role_dicts):
        title_lower = role["title"].lower()
        resp_text = " ".join(role.get("responsibilities", [])).lower()

        for level, expected_signals in TITLE_RESPONSIBILITY_MAP.items():
            if level in title_lower:
                matches = sum(1 for s in expected_signals if s in resp_text)
                if matches >= 2:
                    signals.append(f"Title '{role['title']}' aligns with responsibility depth.")
                else:
                    issues.append(f"Title '{role['title']}' lacks expected responsibility signals ({level}-level scope).")
                break

    for i in range(1, len(role_dicts)):
        prev_resp = " ".join(role_dicts[i - 1].get("responsibilities", [])).lower()
        curr_resp = " ".join(role_dicts[i].get("responsibilities", [])).lower()
        if len(curr_resp.split()) < len(prev_resp.split()) * 0.5:
            issues.append(f"Responsibility depth dropped significantly at '{role_dicts[i]['title']}' — possible misrepresentation.")

    score = max(0, min(100, score))
    reasons = signals + issues
    confidence = "High" if len(signals) >= 3 else "Medium" if len(signals) >= 1 else "Low"

    return {
        "narrative_coherence_score": round(score, 2),
        "confidence": confidence,
        "signals": signals,
        "issues": issues,
        "reasons": reasons,
    }
