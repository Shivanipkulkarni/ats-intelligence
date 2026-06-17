import re
from app.models.schemas import RoleEntry

# Seniority ladder — used to detect promotions
SENIORITY_LADDER = [
    "intern", "trainee", "junior", "associate",
    "mid", "engineer", "developer", "analyst",
    "senior", "lead", "staff", "principal",
    "manager", "director", "vp", "head", "chief", "cto", "ceo"
]

LEADERSHIP_SIGNALS = [
    "led", "managed", "mentored", "directed", "oversaw",
    "hired", "built team", "coordinated", "supervised", "grew team"
]

OWNERSHIP_SIGNALS = [
    "owned", "architected", "designed", "launched", "founded",
    "responsible for", "end-to-end", "drove", "spearheaded", "initiated"
]

GROWTH_SIGNALS = [
    "promoted", "expanded", "increased", "scaled", "improved",
    "optimized", "reduced", "saved", "delivered", "achieved"
]

def seniority_rank(title: str) -> int:
    """Returns rank 0–13 based on title keywords."""
    title_lower = title.lower()
    for i, level in enumerate(SENIORITY_LADDER):
        if level in title_lower:
            return i
    return 4  # default to mid-level if unknown

def extract_duration_months(duration_str: str) -> int:
    """Parse '2 years 3 months', '18 months', '2 yrs' → int months."""
    years = re.findall(r"(\d+)\s*(?:year|yr)", duration_str.lower())
    months = re.findall(r"(\d+)\s*(?:month|mo)", duration_str.lower())
    total = int(years[0]) * 12 if years else 0
    total += int(months[0]) if months else 0
    return total if total > 0 else 12  # default 1 year if unparseable

def signal_count(text: str, signals: list[str]) -> int:
    """Count how many signal phrases appear in text."""
    text_lower = text.lower()
    return sum(1 for s in signals if s in text_lower)

def parse_roles_from_text(resume_text: str) -> list[dict]:
    """
    Heuristic role parser.
    Looks for patterns like:
      Software Engineer | Google | Jan 2020 – Dec 2022
    Returns list of dicts with title, company, duration_months, responsibilities.
    """
    roles = []
    lines = resume_text.split("\n")

    # Regex: match lines with a title + company + date range
    role_pattern = re.compile(
        r"(?P<title>[A-Za-z\s]+(?:engineer|developer|manager|analyst|designer|lead|director|architect|head|officer|intern)[A-Za-z\s]*)"
        r"[\|\-\,at\s]+"
        r"(?P<company>[A-Za-z0-9\s\.\,&]+)"
        r"[\|\-\,\s]*"
        r"(?P<duration>\d+\s*(?:year|yr|month|mo)[s]?\s*(?:\d+\s*(?:month|mo)[s]?)?)?",
        re.IGNORECASE
    )

    current_role = None
    responsibilities = []

    for line in lines:
        line = line.strip()
        if not line:
            if current_role and responsibilities:
                current_role["responsibilities"] = responsibilities
                roles.append(current_role)
                current_role = None
                responsibilities = []
            continue

        match = role_pattern.search(line)
        if match:
            if current_role:
                current_role["responsibilities"] = responsibilities
                roles.append(current_role)
                responsibilities = []

            duration_str = match.group("duration") or "12 months"
            current_role = {
                "title": match.group("title").strip(),
                "company": match.group("company").strip(),
                "duration_months": extract_duration_months(duration_str),
                "responsibilities": [],
            }
        elif current_role and (line.startswith("-") or line.startswith("•") or len(line) > 30):
            responsibilities.append(line.lstrip("-•").strip())

    if current_role:
        current_role["responsibilities"] = responsibilities
        roles.append(current_role)

    return roles