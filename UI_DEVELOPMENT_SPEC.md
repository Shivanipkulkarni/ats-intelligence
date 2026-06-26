# ATS Intelligence Engine - UI Development Specification

## Project Overview

Build a modern web interface for the ATS Intelligence Engine using React + Tailwind CSS (frontend) and FastAPI (backend) with a hybrid storage approach.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (React + Tailwind)                   │
│  - Resume Upload Interface                                       │
│  - Job Description Input                                         │
│  - Real-time Progress Tracking                                   │
│  - Results Dashboard with Filtering                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓ ↑
                         REST API (JSON)
                              ↓ ↑
┌─────────────────────────────────────────────────────────────────┐
│                   Backend API (FastAPI + Python)                 │
│  - File Upload Handler                                           │
│  - Screening Job Queue (Celery)                                  │
│  - Database Operations (PostgreSQL)                              │
│  - ML Pipeline Integration                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓ ↑
    ┌─────────────────────────┴─────────────────────────┐
    ↓                                                     ↓
┌───────────────────────┐                   ┌───────────────────────┐
│   File Storage        │                   │   Database (PostgreSQL)│
├───────────────────────┤                   ├───────────────────────┤
│ /uploads/             │                   │ • users               │
│   session_xxx/        │                   │ • screenings          │
│     resume001.txt     │                   │ • candidates          │
│     resume002.txt     │                   │ • screening_jobs      │
│                       │                   │                       │
│ /cache/               │                   └───────────────────────┘
│   model_abc.pkl       │
│                       │
│ /results/             │
│   screening_xxx.json  │
└───────────────────────┘
```

---

## Tech Stack

### Frontend
- **Framework**: React 18+ with Vite
- **Styling**: Tailwind CSS 3+
- **State Management**: React Query (TanStack Query) + Zustand
- **HTTP Client**: Axios
- **UI Components**: shadcn/ui or Headless UI
- **Charts**: Recharts or Chart.js
- **File Upload**: react-dropzone
- **Notifications**: react-hot-toast

### Backend
- **Framework**: FastAPI (Python 3.10+)
- **Database**: PostgreSQL 14+
- **ORM**: SQLAlchemy 2.0
- **Task Queue**: Celery + Redis
- **File Storage**: Local file system (or AWS S3 optional)
- **Authentication**: JWT (optional for MVP)
- **API Docs**: Auto-generated OpenAPI (Swagger)

### DevOps
- **Containerization**: Docker + Docker Compose
- **Environment**: Python venv, Node 18+
- **Database Migrations**: Alembic

---

## Database Schema

### PostgreSQL Tables

```sql
-- Users table (optional for MVP - can skip auth initially)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Screenings table (main screening sessions)
CREATE TABLE screenings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- Job details
    job_title VARCHAR(500),
    job_description TEXT NOT NULL,
    
    -- Screening configuration
    top_k INTEGER DEFAULT 100,
    use_tiered BOOLEAN DEFAULT TRUE,
    tier1_size INTEGER DEFAULT 40000,
    tier2_size INTEGER DEFAULT 5000,
    custom_weights JSONB,
    
    -- Status tracking
    status VARCHAR(50) NOT NULL, -- 'queued', 'processing', 'completed', 'failed'
    progress_percentage INTEGER DEFAULT 0,
    current_tier INTEGER, -- 1, 2, or 3
    
    -- Metrics
    total_resumes INTEGER,
    elapsed_seconds DECIMAL(10, 2),
    
    -- File paths
    upload_dir VARCHAR(500),
    result_file_path VARCHAR(500),
    cache_dir VARCHAR(500),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Indexes
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_user_id (user_id)
);

-- Candidates table (top N results from each screening)
CREATE TABLE candidates (
    id SERIAL PRIMARY KEY,
    screening_id UUID REFERENCES screenings(id) ON DELETE CASCADE,
    
    -- Candidate info
    resume_id VARCHAR(255) NOT NULL,
    rank INTEGER NOT NULL,
    
    -- Scores
    overall_score DECIMAL(5, 2) NOT NULL,
    semantic_fit DECIMAL(5, 2),
    career_growth DECIMAL(5, 2),
    company_context DECIMAL(5, 2),
    skill_currency DECIMAL(5, 2),
    resilience DECIMAL(5, 2),
    narrative_coherence DECIMAL(5, 2),
    team_portfolio DECIMAL(5, 2),
    artifact_complexity DECIMAL(5, 2),
    counterfactual DECIMAL(5, 2),
    keyword_match DECIMAL(5, 2),
    
    -- Additional data
    reasons JSONB, -- Array of reason strings
    tier1_score DECIMAL(5, 2),
    tier2_score DECIMAL(5, 2),
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_screening_id (screening_id),
    INDEX idx_rank (rank),
    INDEX idx_overall_score (overall_score DESC),
    UNIQUE (screening_id, resume_id)
);

-- Screening jobs table (for Celery task tracking)
CREATE TABLE screening_jobs (
    id UUID PRIMARY KEY,
    screening_id UUID REFERENCES screenings(id) ON DELETE CASCADE,
    celery_task_id VARCHAR(255) UNIQUE,
    status VARCHAR(50), -- 'pending', 'running', 'success', 'failure'
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tier statistics table (detailed tier performance)
CREATE TABLE tier_statistics (
    id SERIAL PRIMARY KEY,
    screening_id UUID REFERENCES screenings(id) ON DELETE CASCADE,
    
    tier1_elapsed DECIMAL(10, 2),
    tier1_cutoff INTEGER,
    tier1_top_score DECIMAL(5, 2),
    tier1_cutoff_score DECIMAL(5, 2),
    
    tier2_elapsed DECIMAL(10, 2),
    tier2_cutoff INTEGER,
    tier2_top_score DECIMAL(5, 2),
    tier2_cutoff_score DECIMAL(5, 2),
    
    tier3_elapsed DECIMAL(10, 2),
    
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## API Specification

### Base URL: `http://localhost:8000/api`

### 1. **Upload Resumes & Start Screening**

**Endpoint**: `POST /screenings`

**Request** (multipart/form-data):
```javascript
{
  files: [File, File, ...],  // Resume files
  job_title: "Senior Python Engineer",
  job_description: "...",
  top_k: 100,
  use_tiered: true,
  tier1_size: 40000,
  tier2_size: 5000,
  custom_weights: {} // optional
}
```

**Response**:
```json
{
  "screening_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Screening job created successfully",
  "total_resumes": 1000,
  "estimated_time_seconds": 120
}
```

---

### 2. **Get Screening Status**

**Endpoint**: `GET /screenings/{screening_id}/status`

**Response**:
```json
{
  "screening_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress_percentage": 65,
  "current_tier": 2,
  "total_resumes": 1000,
  "elapsed_seconds": 45.23,
  "estimated_remaining_seconds": 20,
  "created_at": "2024-01-15T10:30:00Z",
  "started_at": "2024-01-15T10:30:05Z"
}
```

**Status Values**: `queued`, `processing`, `completed`, `failed`

---

### 3. **Get Screening Results**

**Endpoint**: `GET /screenings/{screening_id}/results`

**Query Parameters**:
- `page`: int (default: 1)
- `page_size`: int (default: 25)
- `min_score`: float (optional)
- `sort_by`: string (default: "rank")

**Response**:
```json
{
  "screening_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "job_title": "Senior Python Engineer",
  "total_resumes": 1000,
  "top_k": 100,
  "elapsed_seconds": 67.45,
  "tier_stats": {
    "tier1_elapsed": 23.5,
    "tier1_cutoff": 400,
    "tier2_elapsed": 20.3,
    "tier2_cutoff": 100,
    "tier3_elapsed": 23.65
  },
  "candidates": {
    "total": 100,
    "page": 1,
    "page_size": 25,
    "items": [
      {
        "rank": 1,
        "resume_id": "candidate_042",
        "overall_score": 87.23,
        "all_scores": {
          "semantic_fit": 92.1,
          "career_growth": 78.5,
          "narrative_coherence": 82.0,
          "team_portfolio": 74.2,
          "artifact_complexity": 88.0,
          "counterfactual": 71.5,
          "keyword_match": 68.4
        },
        "reasons": [
          "Strong semantic alignment",
          "Career shows upward trajectory"
        ]
      }
    ]
  },
  "bias_comparison": {
    "overlap_count": 65,
    "overlap_pct": 65.0,
    "lsa_only_count": 35,
    "keyword_only_count": 35
  }
}
```

---

### 4. **Download Full Results (JSON)**

**Endpoint**: `GET /screenings/{screening_id}/download`

**Response**: File download (`screening_{id}.json`)

---

### 5. **Get Screening List** (History)

**Endpoint**: `GET /screenings`

**Query Parameters**:
- `page`: int
- `page_size`: int
- `status`: string (optional filter)

**Response**:
```json
{
  "total": 45,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "screening_id": "550e8400-...",
      "job_title": "Senior Engineer",
      "status": "completed",
      "total_resumes": 1000,
      "top_k": 100,
      "elapsed_seconds": 67.45,
      "created_at": "2024-01-15T10:30:00Z",
      "completed_at": "2024-01-15T10:31:07Z"
    }
  ]
}
```

---

### 6. **Get Candidate Details**

**Endpoint**: `GET /screenings/{screening_id}/candidates/{resume_id}`

**Response**:
```json
{
  "resume_id": "candidate_042",
  "rank": 1,
  "overall_score": 87.23,
  "all_scores": { ... },
  "reasons": [ ... ],
  "tier_scores": {
    "tier1_score": 85.4,
    "tier2_score": 86.7
  },
  "resume_text": "Senior Software Engineer with..." // Optional
}
```

---

### 7. **Delete Screening**

**Endpoint**: `DELETE /screenings/{screening_id}`

**Response**:
```json
{
  "message": "Screening deleted successfully",
  "deleted_files": true
}
```

---

### 8. **WebSocket for Real-time Progress** (Optional)

**Endpoint**: `ws://localhost:8000/ws/screenings/{screening_id}`

**Messages**:
```json
{
  "type": "progress",
  "screening_id": "550e8400-...",
  "progress_percentage": 45,
  "current_tier": 2,
  "message": "Processing Tier 2: 2000/5000 candidates"
}
```

---

## Frontend Pages & Components

### 1. **Home/Dashboard Page**
- Overview of recent screenings
- Quick start button
- Statistics (total screenings, avg processing time)

### 2. **New Screening Page**
- **File Upload Zone** (drag & drop)
  - Support bulk upload
  - Show file list with preview
  - Validate file types (.txt, .json, .jsonl, .pdf)
- **Job Description Input**
  - Rich text editor
  - Save templates
  - Load from file
- **Configuration Panel**
  - Top K selector (slider)
  - Enable/disable tiered filtering
  - Custom tier sizes (advanced)
  - Custom dimension weights (advanced)
- **Submit Button**

### 3. **Screening Progress Page**
- Real-time progress bar
- Current tier indicator
- Live statistics (resumes processed, time elapsed)
- Cancel button
- Tier-by-tier breakdown

### 4. **Results Dashboard Page**
- **Summary Card**
  - Total resumes processed
  - Time elapsed
  - Tier breakdown
- **Candidate Table**
  - Sortable columns (rank, score, etc.)
  - Filterable by score range
  - Expandable rows (show all dimensions)
  - Export to CSV
- **Score Distribution Chart**
  - Histogram of overall scores
  - Dimension radar charts
- **Bias Comparison Section**
  - LSA vs Keyword overlap visualization
- **Individual Candidate Modal**
  - Full score breakdown
  - Reasons display
  - Resume text preview (optional)

### 5. **Screening History Page**
- List of past screenings
- Filter by date, status
- Quick actions (view, download, delete)

---

## File Structure

### Backend Structure
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app
│   ├── config.py                  # Settings
│   ├── database.py                # DB connection
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── screenings.py          # Screening endpoints
│   │   ├── candidates.py          # Candidate endpoints
│   │   └── websocket.py           # WebSocket handler
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── screening.py           # SQLAlchemy models
│   │   ├── candidate.py
│   │   └── user.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── screening.py           # Pydantic schemas
│   │   └── candidate.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── screening_service.py   # Business logic
│   │   ├── file_service.py        # File handling
│   │   └── pipeline_service.py    # ML pipeline wrapper
│   │
│   ├── tasks/
│   │   ├── __init__.py
│   │   └── screening_tasks.py     # Celery tasks
│   │
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
│
├── migrations/                     # Alembic migrations
├── storage/
│   ├── uploads/
│   ├── cache/
│   └── results/
│
├── tests/
├── requirements.txt
├── .env
└── docker-compose.yml
```

### Frontend Structure
```
frontend/
├── src/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Header.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   └── Footer.jsx
│   │   │
│   │   ├── screening/
│   │   │   ├── FileUpload.jsx
│   │   │   ├── JobDescriptionInput.jsx
│   │   │   ├── ConfigPanel.jsx
│   │   │   ├── ProgressTracker.jsx
│   │   │   └── TierIndicator.jsx
│   │   │
│   │   ├── results/
│   │   │   ├── SummaryCard.jsx
│   │   │   ├── CandidateTable.jsx
│   │   │   ├── ScoreChart.jsx
│   │   │   ├── BiasComparison.jsx
│   │   │   └── CandidateModal.jsx
│   │   │
│   │   └── common/
│   │       ├── Button.jsx
│   │       ├── Input.jsx
│   │       ├── Card.jsx
│   │       └── Loader.jsx
│   │
│   ├── pages/
│   │   ├── Dashboard.jsx
│   │   ├── NewScreening.jsx
│   │   ├── ScreeningProgress.jsx
│   │   ├── Results.jsx
│   │   └── History.jsx
│   │
│   ├── hooks/
│   │   ├── useScreening.js
│   │   ├── useWebSocket.js
│   │   └── useFileUpload.js
│   │
│   ├── store/
│   │   └── screeningStore.js      # Zustand store
│   │
│   ├── api/
│   │   └── client.js              # Axios instance
│   │
│   ├── utils/
│   │   └── helpers.js
│   │
│   ├── App.jsx
│   └── main.jsx
│
├── public/
├── index.html
├── tailwind.config.js
├── vite.config.js
└── package.json
```

---

## Key Implementation Details

### 1. **File Upload Flow**

```javascript
// Frontend: FileUpload.jsx
const handleDrop = async (acceptedFiles) => {
  setFiles(acceptedFiles);
  
  // Show preview
  const previews = acceptedFiles.map(file => ({
    name: file.name,
    size: file.size,
    preview: URL.createObjectURL(file)
  }));
  
  setFilePreviews(previews);
};
```

```python
# Backend: screening_service.py
async def create_screening(
    files: List[UploadFile],
    job_description: str,
    config: ScreeningConfig
) -> str:
    # Generate session ID
    screening_id = str(uuid.uuid4())
    
    # Create upload directory
    upload_dir = f"storage/uploads/{screening_id}"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save files
    for file in files:
        file_path = f"{upload_dir}/{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())
    
    # Create DB record
    screening = Screening(
        id=screening_id,
        job_description=job_description,
        status="queued",
        upload_dir=upload_dir,
        ...
    )
    db.add(screening)
    db.commit()
    
    # Queue Celery task
    task = run_screening_task.delay(screening_id)
    
    return screening_id
```

---

### 2. **Celery Task for Screening**

```python
# tasks/screening_tasks.py
from celery import Celery
from app.services.batch.pipeline import BatchPipeline

celery = Celery('ats', broker='redis://localhost:6379/0')

@celery.task(bind=True)
def run_screening_task(self, screening_id: str):
    # Get screening from DB
    screening = db.query(Screening).filter_by(id=screening_id).first()
    
    # Update status
    screening.status = "processing"
    screening.started_at = datetime.now()
    db.commit()
    
    try:
        # Run ML pipeline
        pipeline = BatchPipeline()
        result = pipeline.run_tiered(
            resume_dir=screening.upload_dir,
            job_description=screening.job_description,
            top_k=screening.top_k,
            tier1_size=screening.tier1_size,
            tier2_size=screening.tier2_size
        )
        
        # Save results to file
        result_path = f"storage/results/{screening_id}.json"
        with open(result_path, "w") as f:
            json.dump(result, f)
        
        # Save top candidates to DB
        for candidate_data in result['candidates']:
            candidate = Candidate(
                screening_id=screening_id,
                resume_id=candidate_data['resume_id'],
                rank=candidate_data['rank'],
                overall_score=candidate_data['overall_score'],
                ...
            )
            db.add(candidate)
        
        # Save tier stats
        tier_stats = TierStatistics(
            screening_id=screening_id,
            **result['tier_stats']
        )
        db.add(tier_stats)
        
        # Update screening
        screening.status = "completed"
        screening.completed_at = datetime.now()
        screening.elapsed_seconds = result['elapsed_seconds']
        screening.result_file_path = result_path
        db.commit()
        
    except Exception as e:
        screening.status = "failed"
        db.commit()
        raise
```

---

### 3. **Real-time Progress with WebSocket**

```python
# api/websocket.py
from fastapi import WebSocket

@app.websocket("/ws/screenings/{screening_id}")
async def websocket_endpoint(websocket: WebSocket, screening_id: str):
    await websocket.accept()
    
    while True:
        # Poll DB for progress
        screening = db.query(Screening).filter_by(id=screening_id).first()
        
        await websocket.send_json({
            "type": "progress",
            "progress_percentage": screening.progress_percentage,
            "current_tier": screening.current_tier,
            "status": screening.status
        })
        
        if screening.status in ["completed", "failed"]:
            break
        
        await asyncio.sleep(2)  # Update every 2 seconds
```

```javascript
// Frontend: useWebSocket.js
const useScreeningProgress = (screeningId) => {
  const [progress, setProgress] = useState(0);
  
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/screenings/${screeningId}`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setProgress(data.progress_percentage);
    };
    
    return () => ws.close();
  }, [screeningId]);
  
  return progress;
};
```

---

## Environment Setup

### Backend `.env`
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/ats_intelligence

# Redis
REDIS_URL=redis://localhost:6379/0

# File Storage
UPLOAD_DIR=storage/uploads
CACHE_DIR=storage/cache
RESULTS_DIR=storage/results

# API
API_HOST=0.0.0.0
API_PORT=8000

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Security (optional)
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
```

### Frontend `.env`
```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_WS_BASE_URL=ws://localhost:8000/ws
```

---

## Docker Compose Setup

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: ats_intelligence
      POSTGRES_USER: atsuser
      POSTGRES_PASSWORD: atspass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./backend:/app
      - ./storage:/app/storage
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    env_file:
      - ./backend/.env

  celery:
    build: ./backend
    command: celery -A app.tasks.screening_tasks worker --loglevel=info
    volumes:
      - ./backend:/app
      - ./storage:/app/storage
    depends_on:
      - postgres
      - redis
    env_file:
      - ./backend/.env

  frontend:
    build: ./frontend
    command: npm run dev
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "5173:5173"
    environment:
      - VITE_API_BASE_URL=http://localhost:8000/api

volumes:
  postgres_data:
```

---

## Development Phases

### Phase 1: Backend Foundation (Week 1-2)
1. ✅ Set up FastAPI project structure
2. ✅ Configure PostgreSQL + SQLAlchemy
3. ✅ Create database models and migrations
4. ✅ Implement file upload endpoint
5. ✅ Integrate ML pipeline (existing Python code)
6. ✅ Set up Celery for async tasks

### Phase 2: Core API (Week 2-3)
1. ✅ Implement screening creation endpoint
2. ✅ Implement status tracking
3. ✅ Implement results retrieval with pagination
4. ✅ Add file download endpoint
5. ✅ Write API tests

### Phase 3: Frontend UI (Week 3-4)
1. ✅ Set up React + Vite + Tailwind
2. ✅ Build file upload component
3. ✅ Build job description input
4. ✅ Build progress tracking page
5. ✅ Build results dashboard

### Phase 4: Polish & Deploy (Week 4-5)
1. ✅ Add WebSocket for real-time updates
2. ✅ Implement screening history
3. ✅ Add error handling and validation
4. ✅ Write tests (frontend + backend)
5. ✅ Deploy with Docker Compose

---

## Success Criteria

1. **Functional**:
   - ✅ Users can upload bulk resumes (100+ files)
   - ✅ System processes 1000+ resumes in <2 minutes (with tiering)
   - ✅ Results display all 10 dimension scores
   - ✅ Users can download full JSON results

2. **Performance**:
   - ✅ API response time <100ms (non-screening endpoints)
   - ✅ File upload supports 50MB+ total size
   - ✅ Real-time progress updates <2s latency

3. **UX**:
   - ✅ Intuitive drag-and-drop file upload
   - ✅ Clear progress indicators
   - ✅ Responsive design (mobile-friendly)
   - ✅ Fast table rendering (100+ rows)

---

## Handoff Checklist

### For Backend Team:
- [ ] Review existing Python pipeline code in `app/services/batch/`
- [ ] Set up PostgreSQL database
- [ ] Implement API endpoints per specification
- [ ] Configure Celery for async tasks
- [ ] Write unit tests for endpoints
- [ ] Document API with OpenAPI/Swagger

### For Frontend Team:
- [ ] Set up React + Vite + Tailwind
- [ ] Build responsive UI components
- [ ] Integrate with backend API
- [ ] Implement real-time progress tracking
- [ ] Add data visualization (charts)
- [ ] Write component tests

### For DevOps Team:
- [ ] Set up Docker Compose for development
- [ ] Configure CI/CD pipeline
- [ ] Set up production environment
- [ ] Configure file storage (S3 optional)
- [ ] Monitor performance metrics

---

## Questions for Team?

1. Do we need user authentication for MVP? (Y/N)
2. Should we support PDF resume uploads? (Y/N)
3. Do we need role-based access control? (Y/N)
4. Should results be stored permanently or expire after X days?
5. Do we need email notifications when screening completes?

---

## Contact & Resources

- **Existing ML Pipeline**: `app/services/batch/pipeline.py`
- **Documentation**: `README.md`, `GETTING_STARTED.md`
- **Test Suite**: `test_full_pipeline.py`

**Ready to build! 🚀**
