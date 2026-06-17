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