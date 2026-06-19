from fastapi import APIRouter, HTTPException
from app.models.schemas import SkillDecayRequest, SkillDecayResponse
from app.services.skill_decay.decay_scorer import compute_skill_decay

router = APIRouter(prefix="/skill-decay", tags=["Skill Decay"])

@router.post("/score", response_model=SkillDecayResponse)
def skill_decay(payload: SkillDecayRequest):
    if not payload.resume_text.strip():
        raise HTTPException(status_code=400, detail="Resume text cannot be empty.")

    result = compute_skill_decay(payload.resume_text, payload.roles)
    return SkillDecayResponse(**result)