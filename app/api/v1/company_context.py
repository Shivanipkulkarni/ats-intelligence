from fastapi import APIRouter, HTTPException
from app.models.schemas import CompanyContextRequest, CompanyContextResponse
from app.services.company_context.scorer import compute_company_context

router = APIRouter(prefix="/company", tags=["Company Context"])

@router.post("/context", response_model=CompanyContextResponse)
def company_context(payload: CompanyContextRequest):
    if not payload.resume_text.strip() and not payload.companies:
        raise HTTPException(status_code=400, detail="Provide resume_text or companies list.")

    result = compute_company_context(payload.resume_text, payload.companies)
    return CompanyContextResponse(**result)