# Signals that suggest productive activity during a gap —
# same keyword-signal pattern used in Career Trajectory and Skill Decay.

RECOVERY_SIGNALS = [
    "freelance", "freelancing", "contract", "consulting", "self-employed",
    "certification", "certified", "bootcamp", "course", "completed",
    "founded", "co-founded", "started", "launched", "built",
    "volunteer", "open source", "side project", "upskilled",
    "sabbatical", "career break", "parental leave", "caregiving",
]

MINOR_GAP_THRESHOLD = 3    # months — gaps this short are normal, not flagged at all
SIGNIFICANT_GAP_THRESHOLD = 6   # months — gaps beyond this need real scrutiny


def detect_gaps(roles: list[dict]) -> list[dict]:
    """
    Roles assumed ordered MOST RECENT FIRST (same convention as Skill Decay).
    A 'gap' here is inferred, not date-based — we don't have real calendar
    dates, just durations. So a gap is really: unaccounted time between
    when one role's reported duration ends and the next begins.

    For a hackathon-feasible version, we treat any role with very short
    duration_months relative to its neighbors as a potential gap-filler,
    AND we scan the FULL resume text for explicit gap mentions.
    """
    gaps = []

    # Look for explicit gap mentions in free text across all responsibilities
    # This catches cases where the candidate explicitly explains a gap
    for i in range(len(roles) - 1):
        current_role = roles[i]
        next_role = roles[i + 1]   # next_role is OLDER (earlier in career)

        gap_label = f"Between {next_role.get('title', 'Unknown')} and {current_role.get('title', 'Unknown')}"

        # We don't have real start/end dates, so we can't compute exact
        # calendar gaps. Instead, flag short tenures as potential instability
        # points worth checking for recovery signals nearby.
        current_duration = current_role.get("duration_months", 12)

        if current_duration < MINOR_GAP_THRESHOLD:
            gaps.append({
                "position": gap_label,
                "estimated_months": current_duration,
                "role_text": " ".join(current_role.get("responsibilities", [])),
            })

    return gaps


def find_recovery_signals(text: str) -> list[str]:
    """Scan text for productive/recovery activity signals."""
    text_lower = text.lower()
    found = [signal for signal in RECOVERY_SIGNALS if signal in text_lower]
    return found