import re

SECTION_KEYWORDS = {
    "skills": ["skill", "technologies", "tools", "stack", "proficiency"],
    "experience": ["experience", "work history", "employment", "career"],
    "education": ["education", "degree", "university", "college", "certification"],
    "projects": ["project", "built", "developed", "created", "launched"],
}

def clean_text(text: str) -> str:
    """Lowercase, remove special chars, normalize whitespace."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s\.\,]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_sections(text: str) -> dict[str, str]:
    """
    Heuristically split resume/JD into sections.
    Falls back to full text if no sections detected.
    """
    text_lower = text.lower()
    sections = {}
    lines = text.split("\n")
    current_section = "general"
    buffer = []

    for line in lines:
        matched = False
        for section, keywords in SECTION_KEYWORDS.items():
            if any(kw in line.lower() for kw in keywords) and len(line.strip()) < 60:
                if buffer:
                    sections.setdefault(current_section, "")
                    sections[current_section] += " ".join(buffer)
                current_section = section
                buffer = []
                matched = True
                break
        if not matched:
            buffer.append(line.strip())

    if buffer:
        sections.setdefault(current_section, "")
        sections[current_section] += " ".join(buffer)

    # Always include full text as a section
    sections["full"] = clean_text(text)
    return {k: clean_text(v) for k, v in sections.items() if v.strip()}