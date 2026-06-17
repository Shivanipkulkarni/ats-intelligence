# Scope multiplier logic:
# A startup engineer often owns infra + product + on-call + hiring.
# Same title at FAANG = one narrowly scoped team.
# We reward breadth, not just brand prestige.

KNOWN_ENTERPRISE = {
    "google", "microsoft", "amazon", "meta", "apple", "netflix",
    "ibm", "oracle", "sap", "salesforce", "accenture", "infosys",
    "wipro", "tcs", "cognizant", "deloitte", "pwc", "capgemini",
    "intel", "cisco", "hp", "dell", "jpmorgan", "goldman sachs"
}

KNOWN_UNICORNS = {
    "stripe", "airbnb", "uber", "lyft", "doordash", "coinbase",
    "databricks", "snowflake", "figma", "notion", "canva", "razorpay",
    "zepto", "swiggy", "zomato", "cred", "meesho", "phonepe"
}

STARTUP_SIGNALS = [
    "seed", "early stage", "series a", "pre-revenue", "bootstrapped",
    "stealth", "founded", "co-founded", "startup"
]

ENTERPRISE_SIGNALS = [
    "fortune 500", "fortune500", "publicly traded", "nasdaq", "nyse",
    "bse", "nse", "listed", "global enterprise", "multinational"
]

def classify_company(
    company_name: str,
    employee_count: int | None,
    funding_stage: str | None,
    responsibilities: list[str],
) -> dict:
    """
    Returns:
      stage: "startup" | "scaleup" | "enterprise" | "unknown"
      size_bucket: "micro" | "small" | "mid" | "large" | "unknown"
      scope_multiplier: float (1.0 = neutral, >1.0 = broader scope expected)
    """
    name_lower = company_name.lower()
    resp_text = " ".join(responsibilities).lower()
    stage = "unknown"

    # --- Stage detection ---
    if any(e in name_lower for e in KNOWN_ENTERPRISE):
        stage = "enterprise"
    elif any(u in name_lower for u in KNOWN_UNICORNS):
        stage = "scaleup"
    elif funding_stage:
        fs = funding_stage.lower()
        if any(s in fs for s in ["seed", "series a", "pre-seed", "bootstrapped"]):
            stage = "startup"
        elif any(s in fs for s in ["series b", "series c", "series d"]):
            stage = "scaleup"
        elif any(s in fs for s in ["public", "ipo", "listed"]):
            stage = "enterprise"
    elif any(s in resp_text for s in STARTUP_SIGNALS):
        stage = "startup"
    elif any(s in resp_text for s in ENTERPRISE_SIGNALS):
        stage = "enterprise"

    # --- Size bucket ---
    size_bucket = "unknown"
    if employee_count is not None:
        if employee_count <= 20:
            size_bucket = "micro"
        elif employee_count <= 100:
            size_bucket = "small"
        elif employee_count <= 1000:
            size_bucket = "mid"
        else:
            size_bucket = "large"
    elif stage == "startup":
        size_bucket = "small"
    elif stage == "enterprise":
        size_bucket = "large"

    # --- Scope multiplier ---
    # micro startup = broadest scope, large enterprise = narrowest
    multiplier_map = {
        ("micro",   "startup"):    1.40,
        ("small",   "startup"):    1.30,
        ("small",   "unknown"):    1.20,
        ("mid",     "startup"):    1.20,
        ("mid",     "scaleup"):    1.10,
        ("mid",     "unknown"):    1.05,
        ("large",   "scaleup"):    1.05,
        ("large",   "enterprise"): 0.90,
        ("unknown", "enterprise"): 0.90,
        ("unknown", "startup"):    1.20,
        ("unknown", "scaleup"):    1.05,
        ("unknown", "unknown"):    1.00,
    }
    scope_multiplier = multiplier_map.get((size_bucket, stage), 1.00)

    return {
        "stage": stage,
        "size_bucket": size_bucket,
        "scope_multiplier": scope_multiplier,
    }