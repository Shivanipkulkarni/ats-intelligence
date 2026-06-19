from pydantic import BaseModel

class SemanticFitRequest(BaseModel):
    resume_text: str
    job_description: str

class SemanticFitResponse(BaseModel):
    semantic_fit_score: float          # 0–100
    cosine_similarity: float           # raw -1 to 1
    confidence: str                    # "High" / "Medium" / "Low"
    reasons: list[str]
    section_scores: dict[str, float]   # per-section breakdown

class RoleEntry(BaseModel):
    title: str
    company: str
    duration_months: int
    responsibilities: list[str]

class CareerTrajectoryRequest(BaseModel):
    resume_text: str
    roles: list[RoleEntry] | None = None  # optional structured input

class CareerTrajectoryResponse(BaseModel):
    career_growth_score: float
    confidence: str
    dimension_scores: dict[str, float]   # per-dimension breakdown
    trajectory_label: str                # "Accelerating" / "Steady" / "Plateaued"
    reasons: list[str]

class CompanyEntry(BaseModel):
    company_name: str
    role_title: str
    employee_count: int | None = None        # if known
    funding_stage: str | None = None         # "seed", "series_a", "public", "bootstrapped"
    responsibilities: list[str] = []
    duration_months: int = 12

class CompanyContextRequest(BaseModel):
    resume_text: str
    companies: list[CompanyEntry] | None = None

class CompanyContextResponse(BaseModel):
    company_context_score: float
    confidence: str
    per_company_scores: list[dict]
    scope_multiplier: float          # >1.0 means startup breadth bonus
    reasons: list[str]

class CoreCandidateRequest(BaseModel):
    # Semantic Fit
    resume_text: str
    job_description: str

    # Career Trajectory (optional structured input)
    roles: list[RoleEntry] | None = None

    # Company Context (optional structured input)
    companies: list[CompanyEntry] | None = None

    # Custom weights (optional — let caller tune per role type)
    weights: dict[str, float] | None = None

class ModuleScore(BaseModel):
    score: float
    confidence: str
    reasons: list[str]

class CoreCandidateResponse(BaseModel):
    overall_hidden_talent_score: float
    grade: str                          # A / B / C / D
    verdict: str                        # "Strong Hidden Talent" etc.
    semantic_fit: ModuleScore
    career_growth: ModuleScore
    company_context: ModuleScore
    weights_used: dict[str, float]
    top_reasons: list[str]
    flags: list[str]                    # warnings e.g. "Low confidence on career data"
    
class SkillFreshness(BaseModel):
    skill: str
    last_used_role: str
    months_since_used: int
    freshness_score: float
    decay_category: str

class SkillDecayRequest(BaseModel):
    resume_text: str
    roles: list[RoleEntry] | None = None

class SkillDecayResponse(BaseModel):
    skill_currency_score: float
    confidence: str
    skill_breakdown: list[SkillFreshness]
    reasons: list[str]
class GapAnalysis(BaseModel):
    gap_position: str            # e.g. "Between Engineer and Senior Engineer"
    gap_months: int
    recovery_signals_found: list[str]
    classification: str          # "Adaptive" / "Unexplained" / "Minor"

class CrisisResponseRequest(BaseModel):
    resume_text: str
    roles: list[RoleEntry] | None = None

class CrisisResponseResponse(BaseModel):
    resilience_score: float      # 0-100
    confidence: str
    gaps_detected: list[GapAnalysis]
    reasons: list[str]