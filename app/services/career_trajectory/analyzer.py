from app.services.career_trajectory.extractor import (
    seniority_rank, signal_count,
    LEADERSHIP_SIGNALS, OWNERSHIP_SIGNALS, GROWTH_SIGNALS
)

def analyze_promotions(roles: list[dict]) -> dict:
    """
    Detect upward movement in seniority across roles.
    Score = % of role transitions that were upward.
    """
    if len(roles) < 2:
        return {"score": 50.0, "detail": "Single role — no promotion data."}

    upward = 0
    lateral = 0
    downward = 0

    for i in range(1, len(roles)):
        prev_rank = seniority_rank(roles[i - 1]["title"])
        curr_rank = seniority_rank(roles[i]["title"])
        if curr_rank > prev_rank:
            upward += 1
        elif curr_rank == prev_rank:
            lateral += 1
        else:
            downward += 1

    total = upward + lateral + downward
    score = round(((upward * 1.0 + lateral * 0.5) / total) * 100, 2)
    detail = f"{upward} upward, {lateral} lateral, {downward} downward transitions."
    return {"score": score, "detail": detail}


def analyze_leadership(roles: list[dict]) -> dict:
    """
    Count leadership signals across all responsibility bullets.
    Score increases with more recent and more frequent signals.
    """
    total_signals = 0
    recent_signals = 0
    n = len(roles)

    for i, role in enumerate(roles):
        text = " ".join(role.get("responsibilities", []))
        count = signal_count(text, LEADERSHIP_SIGNALS)
        total_signals += count
        if i >= n - 2:  # last 2 roles weighted as "recent"
            recent_signals += count

    # Normalize: 5+ total signals = strong leadership history
    history_score = min(total_signals / 5.0, 1.0) * 100
    recency_score = min(recent_signals / 3.0, 1.0) * 100
    score = round(history_score * 0.4 + recency_score * 0.6, 2)
    detail = f"{total_signals} leadership signals total, {recent_signals} in recent roles."
    return {"score": score, "detail": detail}


def analyze_ownership(roles: list[dict]) -> dict:
    """
    Detect project ownership / end-to-end responsibility signals.
    """
    total_signals = 0
    for role in roles:
        text = " ".join(role.get("responsibilities", []))
        total_signals += signal_count(text, OWNERSHIP_SIGNALS)

    score = round(min(total_signals / 6.0, 1.0) * 100, 2)
    detail = f"{total_signals} ownership/initiative signals detected."
    return {"score": score, "detail": detail}


def analyze_technical_progression(roles: list[dict]) -> dict:
    """
    Proxy: does the candidate take on more complex technical language over time?
    Measures vocabulary growth in responsibilities across roles.
    """
    if len(roles) < 2:
        return {"score": 50.0, "detail": "Single role — no progression data."}

    vocab_sizes = []
    for role in roles:
        words = set(" ".join(role.get("responsibilities", [])).lower().split())
        vocab_sizes.append(len(words))

    # Score = % of role transitions where vocab grew
    growth_count = sum(
        1 for i in range(1, len(vocab_sizes)) if vocab_sizes[i] > vocab_sizes[i - 1]
    )
    score = round((growth_count / (len(vocab_sizes) - 1)) * 100, 2)
    detail = f"Technical vocabulary grew in {growth_count}/{len(vocab_sizes)-1} role transitions."
    return {"score": score, "detail": detail}


def analyze_tenure(roles: list[dict]) -> dict:
    """
    Penalize very short stints (<12 months), reward healthy tenure (18–48 months).
    Very long stints (>60 months) in same role may signal stagnation — slight penalty.
    """
    if not roles:
        return {"score": 50.0, "detail": "No tenure data."}

    scores = []
    for role in roles:
        months = role.get("duration_months", 12)
        if months < 6:
            scores.append(20.0)   # red flag
        elif months < 12:
            scores.append(50.0)   # short but acceptable
        elif months <= 48:
            scores.append(100.0)  # healthy
        elif months <= 72:
            scores.append(80.0)   # long but okay
        else:
            scores.append(60.0)   # possible stagnation

    score = round(sum(scores) / len(scores), 2)
    detail = f"Average tenure: {round(sum(r['duration_months'] for r in roles)/len(roles))} months/role."
    return {"score": score, "detail": detail}


def analyze_role_transitions(roles: list[dict]) -> dict:
    """
    Detect cross-functional transitions (e.g., engineer → product, IC → manager).
    Reward intentional pivots, not random jumps.
    """
    FUNCTIONAL_GROUPS = {
        "engineering": ["engineer", "developer", "architect", "sre", "devops"],
        "product": ["product", "pm", "product manager"],
        "data": ["data", "analyst", "scientist", "ml", "ai"],
        "management": ["manager", "director", "head", "vp", "lead"],
        "design": ["designer", "ux", "ui"],
    }

    def get_group(title: str) -> str:
        t = title.lower()
        for group, keywords in FUNCTIONAL_GROUPS.items():
            if any(k in t for k in keywords):
                return group
        return "other"

    transitions = []
    for i in range(1, len(roles)):
        g1 = get_group(roles[i - 1]["title"])
        g2 = get_group(roles[i]["title"])
        transitions.append(g1 != g2)

    if not transitions:
        return {"score": 60.0, "detail": "Single role — no transition data."}

    pivot_count = sum(transitions)
    # 1–2 intentional pivots = good, 3+ may signal instability
    if pivot_count == 0:
        score = 70.0   # specialist — consistent, but less breadth
    elif pivot_count <= 2:
        score = 90.0   # intentional cross-functional growth
    else:
        score = 55.0   # too many pivots

    detail = f"{pivot_count} cross-functional transitions detected."
    return {"score": score, "detail": detail}