from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.v1 import semantic, career, company_context, core_score
from app.services.semantic_fit.embedder import get_model

app = FastAPI(
    title="ATS Intelligence Engine",
    description="Hidden Talent Recovery System — Phase 1",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.on_event("startup")
def load_model():
    get_model()

app.include_router(semantic.router,         prefix="/api/v1")
app.include_router(career.router,           prefix="/api/v1")
app.include_router(company_context.router,  prefix="/api/v1")
app.include_router(core_score.router,       prefix="/api/v1")

@app.get("/")
def root():
    return {"status": "ok", "message": "ATS Intelligence Engine is running."}

@app.get("/favicon.ico")
def favicon():
    return {"detail": "No favicon provided."}

@app.get("/health")
def health():
    return {"status": "ok"}