from app.services.skill_decay.skill_extractor import extract_skills_from_text, TECH_KEYWORDS
from app.services.career_trajectory.extractor import parse_roles_from_text

SKILL_DOMAINS = {
    "frontend": {"react", "angular", "vue", "html", "css", "sass", "webpack", "figma", "javascript", "typescript"},
    "backend": {"python", "java", "go", "rust", "c++", "c#", "node", "django", "fastapi", "flask", "spring", "graphql"},
    "data": {"sql", "postgres", "mysql", "mongodb", "redis", "spark", "hadoop", "tableau", "power bi", "machine learning", "deep learning", "nlp", "pytorch", "tensorflow", "excel", "kafka"},
    "infra": {"aws", "gcp", "azure", "kubernetes", "docker", "terraform", "jenkins", "ci/cd", "microservices"},
    "management": {"agile", "scrum", "leadership", "mentor", "managed", "led", "hired", "coordinated", "directed"},
    "llm": {"llm", "nlp", "machine learning", "deep learning", "pytorch", "tensorflow", "rag", "gpt", "transformer"},
}


def compute_team_portfolio(resume_text: str, roles: list | None = None) -> dict:
    if not roles:
        roles = parse_roles_from_text(resume_text)

    all_skills = set(extract_skills_from_text(resume_text))
    role_skills = []

    for role in (roles or []):
        r = role.model_dump() if hasattr(role, "model_dump") else role
        text = " ".join(r.get("responsibilities", [])) + " " + r.get("title", "")
        role_skills.append(set(extract_skills_from_text(text)))

    domains_covered = set()
    for skill in all_skills:
        for domain, domain_skills in SKILL_DOMAINS.items():
            if skill in domain_skills:
                domains_covered.add(domain)

    domain_to_skills = {d: [] for d in SKILL_DOMAINS}
    for skill in all_skills:
        for domain, domain_skills in SKILL_DOMAINS.items():
            if skill in domain_skills:
                domain_to_skills[domain].append(skill)

    non_empty_domains = {d: skills for d, skills in domain_to_skills.items() if skills}
    num_domains = len(non_empty_domains)

    total_skills = len(all_skills)
    domain_breadth_score = min(num_domains / 4.0, 1.0) * 50
    depth_score = min(total_skills / 12.0, 1.0) * 50
    portfolio_score = round(domain_breadth_score + depth_score, 2)

    reasons = []
    if num_domains >= 4:
        reasons.append(f"Broad skill portfolio across {num_domains} domains (T-shaped profile).")
    elif num_domains >= 2:
        reasons.append(f"Moderate breadth across {num_domains} domains.")
    else:
        reasons.append("Narrow skill focus — deep specialist profile.")

    dominant_domain = max(non_empty_domains, key=lambda d: len(non_empty_domains[d])) if non_empty_domains else None
    if dominant_domain:
        skills_list = ", ".join(non_empty_domains[dominant_domain][:4])
        reasons.append(f"Strongest domain: {dominant_domain} ({skills_list}).")

    confidence = "High" if num_domains >= 3 and total_skills >= 8 else "Medium" if num_domains >= 1 else "Low"

    return {
        "team_portfolio_score": portfolio_score,
        "confidence": confidence,
        "domains_covered": list(domains_covered),
        "domain_breakdown": {d: s for d, s in non_empty_domains.items()},
        "total_skills_detected": total_skills,
        "reasons": reasons,
    }
