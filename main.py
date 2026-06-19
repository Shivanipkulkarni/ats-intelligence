from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.v1 import semantic, career, company_context, core_score, pdf, skill_decay, crisis_response

app = FastAPI(
    title="ATS Intelligence Engine",
    description="Hidden Talent Recovery System — Phase 1",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(semantic.router,         prefix="/api/v1")
app.include_router(career.router,           prefix="/api/v1")
app.include_router(company_context.router,  prefix="/api/v1")
app.include_router(core_score.router,       prefix="/api/v1")
app.include_router(pdf.router,              prefix="/api/v1")
app.include_router(skill_decay.router,      prefix="/api/v1")
app.include_router(crisis_response.router,  prefix="/api/v1")

@app.get("/")
def root():
    return {"status": "ok", "message": "ATS Intelligence Engine is running."}

@app.get("/favicon.ico")
def favicon():
    return {"detail": "No favicon provided."}

@app.get("/health")
def health():
    return {"status": "ok"}