CROSS_FUNCTIONAL_SIGNALS = [
    "product", "design", "marketing", "sales", "operations",
    "finance", "legal", "hr", "recruiting", "strategy", "bd",
    "business development", "customer success", "support"
]

INFRA_SIGNALS = [
    "infra", "infrastructure", "devops", "ci/cd", "deployment",
    "on-call", "monitoring", "alerting", "sre", "platform"
]

OWNERSHIP_DEPTH_SIGNALS = [
    "end-to-end", "full stack", "zero to one", "0 to 1",
    "from scratch", "greenfield", "sole", "single-handedly", "wore many hats"
]

IMPACT_SIGNALS = [
    "revenue", "cost", "latency", "uptime", "users", "conversion",
    "retention", "growth", "scale", "%", "x faster", "x reduction"
]

def analyze_scope(responsibilities: list[str], role_title: str) -> dict:
    """
    Returns a scope_score (0–100) and detected breadth signals.
    """
    text = " ".join(responsibilities).lower()
    title_lower = role_title.lower()

    cross_functional = sum(1 for s in CROSS_FUNCTIONAL_SIGNALS if s in text)
    infra_breadth = sum(1 for s in INFRA_SIGNALS if s in text)
    ownership_depth = sum(1 for s in OWNERSHIP_DEPTH_SIGNALS if s in text)
    impact_count = sum(1 for s in IMPACT_SIGNALS if s in text)

    # Normalize each signal group to 0–25 range, total = 0–100
    score = (
        min(cross_functional / 3.0, 1.0) * 25 +
        min(infra_breadth   / 3.0, 1.0) * 20 +
        min(ownership_depth / 2.0, 1.0) * 30 +
        min(impact_count    / 4.0, 1.0) * 25
    )

    detected = []
    if cross_functional >= 2:
        detected.append("Cross-functional collaboration detected.")
    if infra_breadth >= 2:
        detected.append("Infrastructure/platform ownership signals found.")
    if ownership_depth >= 1:
        detected.append("End-to-end or sole ownership language used.")
    if impact_count >= 2:
        detected.append("Quantified business/technical impact mentioned.")

    return {
        "scope_score": round(score, 2),
        "breadth_signals": detected,
    }