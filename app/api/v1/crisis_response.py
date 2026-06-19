from fastapi import APIRouter, HTTPException
from app.models.schemas import CrisisResponseRequest, CrisisResponseResponse
from app.services.crisis_response.pivot_scorer import compute_crisis_response

router = APIRouter(prefix="/crisis-response", tags=["Crisis Response"])

@router.post("/score", response_model=CrisisResponseResponse)
def crisis_response(payload: CrisisResponseRequest):
    if not payload.resume_text.strip() and not payload.roles:
        raise HTTPException(status_code=400, detail="Provide resume_text or roles.")

    result = compute_crisis_response(payload.resume_text, payload.roles)
    return CrisisResponseResponse(**result)