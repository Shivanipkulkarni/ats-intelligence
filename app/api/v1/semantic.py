from fastapi import APIRouter, HTTPException
from app.models.schemas import SemanticFitRequest, SemanticFitResponse
from app.services.semantic_fit.scorer import compute_semantic_fit

router = APIRouter(prefix="/semantic", tags=["Semantic Fit"])

@router.post("/fit", response_model=SemanticFitResponse)
def semantic_fit(payload: SemanticFitRequest):
    if not payload.resume_text.strip() or not payload.job_description.strip():
        raise HTTPException(status_code=400, detail="Resume and job description cannot be empty.")
    
    result = compute_semantic_fit(payload.resume_text, payload.job_description)
    return SemanticFitResponse(**result)