from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

router = APIRouter(prefix="/pdf", tags=["PDF Processing"])

class PDFScoringResult(BaseModel):
    semantic_fit: dict
    career_trajectory: dict
    company_context: dict
    overall_score: dict

@router.post("/score", response_model=PDFScoringResult)
async def score_from_pdf(resume_pdf: UploadFile = File(...), jd_pdf: UploadFile = File(...)):
    """
    Upload resume and job description PDFs, extract text, and compute all scores.
    """
    # Lazy imports to avoid blocking startup
    from app.services.pdf_extractor import extract_text_from_pdf
    from app.services.semantic_fit.scorer import compute_semantic_fit
    from app.services.career_trajectory.scorer import compute_career_trajectory
    from app.services.company_context.scorer import compute_company_context
    from app.services.core_score.aggregator import compute_core_score
    
    try:
        # Read PDF files
        resume_bytes = await resume_pdf.read()
        jd_bytes = await jd_pdf.read()
        
        # Extract text from PDFs
        resume_text = extract_text_from_pdf(resume_bytes)
        jd_text = extract_text_from_pdf(jd_bytes)
        
        if not resume_text.strip() or not jd_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDFs")
        
        # Compute semantic fit
        semantic_result = compute_semantic_fit(resume_text, jd_text)
        
        # Compute career trajectory
        career_result = compute_career_trajectory(resume_text)
        
        # Compute company context
        company_result = compute_company_context(resume_text)
        
        # Compute overall score
        overall_result = compute_core_score(resume_text, jd_text)
        
        return PDFScoringResult(
            semantic_fit=semantic_result,
            career_trajectory=career_result,
            company_context=company_result,
            overall_score=overall_result
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDFs: {str(e)}")


@router.post("/extract-resume")
async def extract_resume_text(file: UploadFile = File(...)):
    """Extract text from resume PDF only."""
    from app.services.pdf_extractor import extract_text_from_pdf
    
    try:
        pdf_bytes = await file.read()
        text = extract_text_from_pdf(pdf_bytes)
        return {"resume_text": text}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/extract-jd")
async def extract_jd_text(file: UploadFile = File(...)):
    """Extract text from job description PDF only."""
    from app.services.pdf_extractor import extract_text_from_pdf
    
    try:
        pdf_bytes = await file.read()
        text = extract_text_from_pdf(pdf_bytes)
        return {"job_description": text}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
