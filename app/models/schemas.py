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