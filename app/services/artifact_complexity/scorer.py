import re
from app.services.career_trajectory.extractor import parse_roles_from_text

COMPLEXITY_SIGNALS_HIGH = [
    r"\b(architect(?:ed|ure)?)\b", r"\b(designed?)\b", r"\b(scaled?)\b",
    r"\b(distributed)\b", r"\b(microservices)\b", r"\b(high.?availabilit)\b",
    r"\b(millions?)\b", r"\b(billions?)\b", r"\b( petabytes?|terabytes?|gigabytes?)\b",
    r"\b(low.?latency)\b", r"\b(real.?time)\b", r"\b(fault.?toleran)\b",
    r"\b( multi.?tenant)\b", r"\b(concurr?en)\b", r"\b(optimized?|optimization)\b",
    r"\b( zero.?downtime)\b", r"\b(disaster.?recover)\b",
    r"\b(cross.?function)\b", r"\b( end.?to.?end)\b",
    r"\b(greenfield|from.?scratch|zero.?to.?one|0.?to.?1)\b",
    r"\b(kubernetes|k8s|docker|containers?)\b",
    r"\b(pipeline|ci/cd|deployment)\b",
    r"\b(machine.?learn|deep.?learn|nlp|llm|recommend)\b",
]

COMPLEXITY_SIGNALS_MEDIUM = [
    r"\b(implemented?|built|developed?|created?)\b",
    r"\b(integration|api|rest|graphql)\b",
    r"\b(database|sql|nosql)\b",
    r"\b(framework|library|sdk)\b",
    r"\b(test(?:ing|s)?)\b", r"\b(deploy)\b",
    r"\b(monitoring|observability|logging)\b",
    r"\b(agile|scrum|sprint)\b",
    r"\b(mentor|lead|managed)\b",
]


def compute_artifact_complexity(resume_text: str, roles: list | None = None) -> dict:
    if not roles:
        roles = parse_roles_from_text(resume_text)

    texts_to_scan = [resume_text]
    for role in (roles or []):
        r = role.model_dump() if hasattr(role, "model_dump") else role
        texts_to_scan.append(" ".join(r.get("responsibilities", [])))

    combined = " ".join(texts_to_scan).lower()

    high_count = 0
    for pattern in COMPLEXITY_SIGNALS_HIGH:
        high_count += len(re.findall(pattern, combined))

    medium_count = 0
    for pattern in COMPLEXITY_SIGNALS_MEDIUM:
        medium_count += len(re.findall(pattern, combined))

    high_score = min(high_count / 5.0, 1.0) * 60
    medium_score = min(medium_count / 10.0, 1.0) * 40
    raw_score = high_score + medium_score

    complexity_score = round(raw_score, 2)

    reasons = []
    if high_count >= 5:
        reasons.append("High-complexity projects detected: distributed systems, scale, or infrastructure work.")
    elif high_count >= 2:
        reasons.append("Moderate technical complexity — some advanced engineering signals found.")
    else:
        reasons.append("Limited complexity signals — role may involve straightforward implementation.")

    if high_count > 0:
        reasons.append(f"{high_count} high-complexity signals and {medium_count} medium-complexity signals detected.")

    confidence = "High" if high_count >= 5 else "Medium" if high_count >= 1 else "Low"

    return {
        "artifact_complexity_score": complexity_score,
        "confidence": confidence,
        "high_complexity_signals": high_count,
        "medium_complexity_signals": medium_count,
        "reasons": reasons,
    }
