import re

TECH_KEYWORDS = [
    "python", "java", "javascript", "typescript", "go", "rust", "c++", "c#",
    "react", "angular", "vue", "node", "django", "fastapi", "flask", "spring",
    "aws", "gcp", "azure", "kubernetes", "docker", "terraform", "jenkins",
    "sql", "postgres", "mysql", "mongodb", "redis", "kafka", "spark", "hadoop",
    "machine learning", "deep learning", "llm", "nlp", "pytorch", "tensorflow",
    "git", "ci/cd", "rest", "graphql", "microservices", "agile", "scrum",
    "html", "css", "sass", "webpack", "figma", "tableau", "power bi", "excel",
]

FAST_DECAY_SKILLS = {
    "react", "angular", "vue", "webpack", "figma", "kafka", "spring",
    "django", "fastapi", "flask", "jenkins", "tableau", "power bi",
}

SLOW_DECAY_SKILLS = {
    "python", "java", "sql", "git", "agile", "scrum", "c++", "c#",
    "aws", "gcp", "azure", "kubernetes", "docker", "postgres", "mysql",
}


def extract_skills_from_text(text: str) -> list[str]:
    text_lower = text.lower()
    found = []
    for kw in TECH_KEYWORDS:
        if kw in text_lower:
            found.append(kw)
    return found


def get_decay_speed(skill: str) -> str:
    if skill in FAST_DECAY_SKILLS:
        return "fast"
    elif skill in SLOW_DECAY_SKILLS:
        return "slow"
    return "medium"


def map_skills_to_roles(roles: list[dict]) -> dict[str, dict]:
    skill_last_seen = {}
    months_elapsed = 0

    for role in roles:
        text = " ".join(role.get("responsibilities", []))
        skills_in_role = extract_skills_from_text(text)

        for skill in skills_in_role:
            if skill not in skill_last_seen:
                skill_last_seen[skill] = {
                    "role_title": role.get("title", "Unknown"),
                    "months_ago": months_elapsed,
                }

        months_elapsed += role.get("duration_months", 12)

    return skill_last_seen