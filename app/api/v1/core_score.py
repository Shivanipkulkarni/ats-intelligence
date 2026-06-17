from fastapi import APIRouter, HTTPException
from app.models.schemas import CoreCandidateRequest, CoreCandidateResponse, ModuleScore
from app.services.core_score.aggregator import compute_core_score

router = APIRouter(prefix="/candidate", tags=["Core Candidate Score"])

@router.post("/score", response_model=CoreCandidateResponse)
def core_candidate_score(payload: CoreCandidateRequest):
    if not payload.resume_text.strip() or not payload.job_description.strip():
        raise HTTPException(status_code=400, detail="resume_text and job_description are required.")

    result = compute_core_score(
        resume_text=payload.resume_text,
        job_description=payload.job_description,
        roles=payload.roles,
        companies=payload.companies,
        weights=payload.weights,
    )

    return CoreCandidateResponse(
        overall_hidden_talent_score=result["overall_hidden_talent_score"],
        grade=result["grade"],
        verdict=result["verdict"],
        semantic_fit=ModuleScore(**result["semantic_fit"]),
        career_growth=ModuleScore(**result["career_growth"]),
        company_context=ModuleScore(**result["company_context"]),
        weights_used=result["weights_used"],
        top_reasons=result["top_reasons"],
        flags=result["flags"],
    )