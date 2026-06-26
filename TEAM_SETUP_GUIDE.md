# 🚀 Team Setup Guide - ATS Intelligence Engine

> **Quick Reference for Team Members**: Complete guide to clone, setup, run screening, and build the UI

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Initial Setup (5 minutes)](#initial-setup)
3. [Running Your First Screening](#running-your-first-screening)
4. [Understanding the Output](#understanding-the-output)
5. [Building the Web UI](#building-the-web-ui)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)

---

## 🎯 Project Overview

**What does this do?**
This is an AI-powered resume screening system that ranks candidates using 10 scoring dimensions (not just keyword matching). It can process 200K resumes in ~2 minutes.

**Tech Stack:**
- **Current**: Python CLI with scikit-learn (TF-IDF + LSA)
- **UI to Build**: React + Tailwind (frontend), FastAPI (backend), PostgreSQL (database)

**Key Features:**
- Semantic similarity (beyond keywords)
- Career trajectory analysis
- 3-tier filtering for performance (200K→40K→5K→100)
- Offline processing (no GPU, no internet needed)

---

## 🔧 Initial Setup

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd ats-intelligence
```

### Step 2: Create Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

Expected packages:
- scikit-learn (ML)
- numpy, scipy (math operations)
- joblib (model serialization)
- pydantic (data validation)

### Step 4: Verify Installation

```bash
python -c "import sklearn; print('✓ scikit-learn installed')"
python -c "import numpy; print('✓ numpy installed')"
```

---

## 🎬 Running Your First Screening

### Quick Test (5 minutes)

#### 1. Create Test Data

**Create folder:**
```bash
mkdir resumes
```

**Create `resumes/resumes.jsonl`:**
```jsonl
{"id": "001", "resume_text": "Senior Software Engineer with 8 years Python experience. Built distributed systems at Google, led team of 5 engineers, expertise in AWS, Kubernetes, microservices architecture."}
{"id": "002", "resume_text": "Junior Frontend Developer with 2 years React and JavaScript experience. Built responsive web applications, worked with REST APIs."}
{"id": "003", "resume_text": "Full Stack Engineer with 6 years experience. Python backend with Django, React frontend, PostgreSQL databases, Docker deployment."}
```

**Create `job_description.txt`:**
```
Senior Backend Engineer

We need an experienced engineer to lead our backend team.

Requirements:
- 5+ years software engineering
- Python expertise
- Distributed systems and microservices
- AWS or cloud platforms
- Team leadership experience
```

#### 2. Run Screening

**Basic mode (for small datasets):**
```bash
python run_screening.py \
  --resume-dir ./resumes \
  --jd-file ./job_description.txt \
  --top-k 10
```

**Fast mode (for 50K+ resumes):**
```bash
python run_screening.py \
  --resume-dir ./resumes \
  --jd-file ./job_description.txt \
  --top-k 10 \
  --tiered \
  --workers 4
```

**Save to file:**
```bash
python run_screening.py \
  --resume-dir ./resumes \
  --jd-file ./job_description.txt \
  --top-k 10 \
  --output results.json
```

#### 3. View Results

Results will show:
```
================================================================================
SCREENING RESULTS
================================================================================
Processed 3 resumes in 2.34s

Top 10 Candidates:
--------------------------------------------------------------------------------
  #  1 | 001                                   | Score: 87.23
  #  2 | 003                                   | Score: 76.45
  #  3 | 002                                   | Score: 58.91
```

---

## 📊 Understanding the Output

### Console Output Breakdown

```
#  1 | 001 | Score: 87.23
```
- `#1` = Rank
- `001` = Resume ID
- `87.23` = Overall weighted score (0-100)

### JSON Output Structure

**File: `results.json`**

```json
{
  "total_resumes_processed": 3,
  "elapsed_seconds": 2.34,
  "candidates": [
    {
      "rank": 1,
      "resume_id": "001",
      "overall_score": 87.23,
      "all_scores": {
        "semantic_fit": 92.1,        // Resume-JD meaning similarity
        "career_growth": 78.5,       // Promotion velocity
        "narrative_coherence": 82.0, // Career story consistency
        "team_portfolio": 74.2,      // Skill breadth
        "artifact_complexity": 88.0, // Project difficulty
        "skill_currency": 60.0,      // Skill recency
        "resilience": 65.0,          // Career gaps/pivots
        "company_context": 65.0,     // Company type experience
        "counterfactual": 71.5,      // Outperformance
        "keyword_match": 68.4        // Traditional matching (not in final score)
      },
      "reasons": [
        "Strong semantic alignment",
        "Career shows upward trajectory",
        "Broad skill portfolio across 4 domains"
      ]
    }
  ]
}
```

### 10 Scoring Dimensions Explained

| Dimension | Weight | Measures |
|-----------|--------|----------|
| **Semantic Fit** | 25% | How well resume matches JD meaning (not just keywords) |
| **Career Growth** | 15% | Promotions, leadership signals |
| **Narrative Coherence** | 10% | Does title match responsibilities? |
| **Team Portfolio** | 10% | T-shaped (broad) vs specialist |
| **Artifact Complexity** | 10% | Difficult projects (distributed systems, scale) |
| **Skill Currency** | 10% | Recent, relevant skills |
| **Resilience** | 10% | How gaps/pivots were handled |
| **Company Context** | 5% | Startup vs enterprise experience |
| **Counterfactual** | 5% | Better than expected trajectory |
| **Keyword Match** | 0%* | Traditional overlap (for comparison only) |

---

## 🌐 Building the Web UI

### Overview

Your task is to build a React + Tailwind web interface that wraps this CLI tool.

**What you'll build:**
1. **Frontend**: React app with resume upload, JD input, real-time progress, results dashboard
2. **Backend**: FastAPI wrapper around the Python screening engine
3. **Database**: PostgreSQL to store screening metadata and top results
4. **Storage**: Hybrid approach (files for resumes/models, DB for metadata)

### Complete Specification

👉 **Read `UI_DEVELOPMENT_SPEC.md`** for:
- Complete architecture diagram
- Database schema (PostgreSQL tables)
- API specification (8 REST endpoints + WebSocket)
- Frontend page mockups and components
- Docker Compose setup
- 5-week development roadmap

### Quick Start for UI Development

#### 1. Read the UI Spec First

```bash
# Open in your editor
code UI_DEVELOPMENT_SPEC.md

# Or view in browser (if you have a markdown viewer)
```

**Key sections:**
- **Architecture Overview** (page 1) - System design
- **Database Schema** (page 2-3) - PostgreSQL tables
- **API Specification** (page 4-7) - REST endpoints
- **Frontend Pages** (page 8-10) - UI components
- **Development Roadmap** (page 11) - 5-week plan

#### 2. Setup Development Environment

**Backend (FastAPI):**
```bash
cd backend/  # You'll create this
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install fastapi uvicorn sqlalchemy psycopg2-binary celery redis
```

**Frontend (React):**
```bash
cd frontend/  # You'll create this
npm create vite@latest . -- --template react
npm install
npm install -D tailwindcss postcss autoprefixer
npm install axios react-query zustand react-dropzone recharts
```

**Database (PostgreSQL):**
```bash
# Using Docker Compose (recommended)
docker-compose up -d postgres redis
```

#### 3. Integrate with Existing Screening Engine

The core screening logic is already in `app/services/batch/pipeline.py`.

**Your backend needs to:**
1. Accept resume uploads via API
2. Save files to disk
3. Call the existing `BatchPipeline` class
4. Stream progress via WebSocket
5. Store results in PostgreSQL

**Example integration:**

```python
# backend/app/services/screening.py
from app.services.batch.pipeline import BatchPipeline

def run_screening_job(screening_id: str, resume_dir: str, jd_text: str):
    """Wrapper around existing screening engine"""
    pipeline = BatchPipeline(
        resume_dir=resume_dir,
        use_tiered=True,
        workers=8
    )
    
    results = pipeline.run_tiered(
        jd_text=jd_text,
        top_k=100
    )
    
    # Save to database
    save_results_to_db(screening_id, results)
    
    return results
```

#### 4. Follow the Development Roadmap

**Week 1-2: Backend Foundation**
- Setup FastAPI project
- Create database models (SQLAlchemy)
- Implement file upload endpoints
- Integrate with existing screening engine

**Week 3: Async Processing**
- Setup Celery + Redis
- Create background job queue
- Implement WebSocket progress streaming

**Week 4: Frontend**
- Setup React + Tailwind
- Build upload interface
- Create results dashboard
- Add filtering/sorting

**Week 5: Polish & Deploy**
- Error handling
- Loading states
- Docker deployment
- Testing

---

## 🧪 Testing

### Test the CLI Implementation

**Quick test (1000 resumes):**
```bash
python test_tiers_quick.py
```

**Full test (500 resumes):**
```bash
python test_full_pipeline.py
```

Expected output:
```
🎉 ALL TESTS PASSED!
Tier 1 and Tier 2 are working correctly!
```

### Test Your Own Data

```bash
# Test with your resumes
python run_screening.py \
  --resume-dir /path/to/your/resumes \
  --jd-file /path/to/your/jd.txt \
  --top-k 20 \
  --output test_results.json

# Verify output
cat test_results.json
```

---

## 🔥 Common Commands Reference

### Standard Screening (Small Dataset)
```bash
python run_screening.py --resume-dir ./resumes --jd-file ./jd.txt --top-k 50
```

### Fast Screening (Large Dataset)
```bash
python run_screening.py --resume-dir ./resumes --jd-file ./jd.txt --tiered --workers 8 --top-k 100
```

### Save Results to File
```bash
python run_screening.py --resume-dir ./resumes --jd-file ./jd.txt --output results.json
```

### Custom Weights (Emphasize Leadership)
```bash
python run_screening.py \
  --resume-dir ./resumes \
  --jd-file ./jd.txt \
  --weights '{"semantic_fit":0.3,"career_growth":0.25,"team_portfolio":0.2}'
```

### Cache Model (Reuse for Multiple JDs)
```bash
# First run
python run_screening.py --resume-dir ./resumes --jd-file ./jd1.txt --cache-dir ./cache

# Subsequent runs (faster!)
python run_screening.py --resume-dir ./resumes --jd-file ./jd2.txt --cache-dir ./cache --from-cache
```

---

## 🐛 Troubleshooting

### Issue: "No module named 'sklearn'"

**Solution:**
```bash
pip install scikit-learn
```

### Issue: "No resumes found in directory"

**Solution:**
- Check file format (must be `.jsonl`, `.json`, or `.txt`)
- Verify path is correct
- Check files aren't empty

### Issue: Screening is very slow

**Solution:**
- Use `--tiered` flag for 50K+ resumes
- Don't use `--tiered` for <5K resumes (overhead)
- Increase `--workers` to match CPU cores

### Issue: Out of memory

**Solution:**
```bash
# Use tiered mode (reduces memory)
python run_screening.py --resume-dir ./resumes --jd-file ./jd.txt --tiered
```

### Issue: Can't find `run_screening.py`

**Solution:**
```bash
# Make sure you're in the project root
cd ats-intelligence
ls  # You should see run_screening.py
```

---

## 📚 Additional Resources

### Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Project overview, Quick Start |
| `GETTING_STARTED.md` | Detailed CLI usage guide |
| `UI_DEVELOPMENT_SPEC.md` | Complete UI build specification |
| `TEAM_SETUP_GUIDE.md` | This file - team onboarding |

### Code Structure

| Path | Purpose |
|------|---------|
| `run_screening.py` | CLI entry point |
| `app/services/batch/pipeline.py` | Main screening engine |
| `app/services/batch/semantic_engine.py` | TF-IDF + LSA |
| `app/services/career_trajectory/` | Career analysis |
| `app/services/*/` | Other scoring dimensions |

### Key Concepts

**3-Tier Filtering:**
```
200K resumes → Tier 1 (semantic) → 40K
40K resumes → Tier 2 (medium heuristics) → 5K
5K resumes → Tier 3 (deep analysis) → Top 100
```

**When to use tiered:**
- ✅ Use for 50K+ resumes
- ❌ Skip for <5K resumes

---

## ✅ Checklist for Team Members

### Backend/Full-Stack Developer
- [ ] Clone repo and install dependencies
- [ ] Run test screening with sample data
- [ ] Read `UI_DEVELOPMENT_SPEC.md` completely
- [ ] Setup FastAPI backend project
- [ ] Create PostgreSQL database schema
- [ ] Implement file upload endpoints
- [ ] Integrate with `BatchPipeline` class
- [ ] Setup Celery for async jobs
- [ ] Implement WebSocket progress streaming

### Frontend Developer
- [ ] Clone repo and install dependencies
- [ ] Run test screening to understand output format
- [ ] Read `UI_DEVELOPMENT_SPEC.md` sections on frontend
- [ ] Setup React + Vite project
- [ ] Configure Tailwind CSS
- [ ] Build upload interface with react-dropzone
- [ ] Create results dashboard
- [ ] Implement filtering/sorting on results
- [ ] Add progress indicators

### DevOps/Deployment
- [ ] Review Docker Compose setup in UI spec
- [ ] Setup PostgreSQL + Redis containers
- [ ] Configure environment variables
- [ ] Setup CI/CD pipeline (optional)
- [ ] Plan production deployment

---

## 🤝 Need Help?

### Questions About:

**CLI Usage** → Check `GETTING_STARTED.md`

**UI Architecture** → Check `UI_DEVELOPMENT_SPEC.md`

**Code Structure** → Check `README.md` Project Structure section

**Scoring Logic** → Check `README.md` 10 Scoring Dimensions section

**API Design** → Check `UI_DEVELOPMENT_SPEC.md` API Specification section

---

## 🎯 Next Steps

1. ✅ Complete initial setup
2. ✅ Run your first test screening
3. ✅ Read `UI_DEVELOPMENT_SPEC.md` thoroughly
4. 🚀 Start building the UI (follow 5-week roadmap)
5. 🧪 Test and iterate

**Remember**: The core screening engine is already built and tested. Your job is to wrap it with a beautiful, user-friendly web interface!

Good luck! 🚀
