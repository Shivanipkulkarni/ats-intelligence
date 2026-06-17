from fastapi import APIRouter, HTTPException
from app.models.schemas import CareerTrajectoryRequest, CareerTrajectoryResponse
from app.services.career_trajectory.scorer import compute_career_trajectory

router = APIRouter(prefix="/career", tags=["Career Trajectory"])

@router.post("/trajectory", response_model=CareerTrajectoryResponse)
def career_trajectory(payload: CareerTrajectoryRequest):
    if not payload.resume_text.strip():
        raise HTTPException(status_code=400, detail="Resume text cannot be empty.")

    result = compute_career_trajectory(payload.resume_text, payload.roles)
    return CareerTrajectoryResponse(**result)