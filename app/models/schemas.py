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

class NarrativeCoherenceResponse(BaseModel):
    narrative_coherence_score: float
    confidence: str
    signals: list[str] = []
    issues: list[str] = []
    reasons: list[str]

class TeamPortfolioResponse(BaseModel):
    team_portfolio_score: float
    confidence: str
    domains_covered: list[str] = []
    domain_breakdown: dict[str, list[str]] = {}
    total_skills_detected: int = 0
    reasons: list[str]

class ArtifactComplexityResponse(BaseModel):
    artifact_complexity_score: float
    confidence: str
    high_complexity_signals: int = 0
    medium_complexity_signals: int = 0
    reasons: list[str]

class CounterfactualResponse(BaseModel):
    counterfactual_score: float
    confidence: str
    avg_seniority_beat: float = 0.0
    projections_analyzed: int = 0
    reasons: list[str]

class KeywordMatchResponse(BaseModel):
    keyword_match_score: float
    skill_match_rate: float
    skills_in_jd: int = 0
    skills_matched: int = 0
    term_overlap_pct: float = 0.0
    bigram_overlap_pct: float = 0.0
    years_experience_match: float = 0.0
    jd_years_required: float = 0.0
    resume_years_mentioned: float = 0.0
    skill_breakdown: list[dict] = []

class BatchResumeRecord(BaseModel):
    resume_id: str
    resume_text: str
    semantic_fit_score: float = 0.0
    career_growth_score: float = 0.0
    company_context_score: float = 0.0
    skill_currency_score: float = 0.0
    resilience_score: float = 0.0
    narrative_coherence_score: float = 0.0
    team_portfolio_score: float = 0.0
    artifact_complexity_score: float = 0.0
    counterfactual_score: float = 0.0
    keyword_match_score: float = 0.0
    overall_score: float = 0.0

class CandidateResult(BaseModel):
    rank: int
    resume_id: str
    overall_score: float
    all_scores: dict[str, float]
    reasons: list[str] = []

class BiasComparisonSummary(BaseModel):
    overlap_count: int
    overlap_pct: float
    lsa_only_count: int
    keyword_only_count: int
    avg_rank_shift: float

class BiasComparisonResult(BaseModel):
    summary: BiasComparisonSummary
    examples: dict

class ScreeningResponse(BaseModel):
    job_title: str = ""
    top_k: int = 100
    total_resumes_processed: int
    elapsed_seconds: float
    candidates: list[CandidateResult]
    lsa_ranking: list[CandidateResult]
    keyword_ranking: list[CandidateResult]
    bias_comparison: BiasComparisonResult | None = None