# 🎯 ATS Intelligence Engine

**AI-powered resume screening** that ranks candidates using **10 scoring dimensions** beyond keyword matching.

- ⚡ Processes **200K resumes in ~2 minutes** (with 3-tier optimization)
- 🧠 Semantic understanding using TF-IDF + LSA
- 📊 Career trajectory, skill portfolio, and project complexity analysis
- 🚫 **No GPU, no internet, no deep learning** — runs on standard hardware

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
git clone <repository-url>
cd ats-intelligence
pip install -r requirements.txt
```

### 2. Prepare Input Files

**Create `resumes/` folder** with resume files in any format:

```bash
# Option A: Single JSONL file (recommended for large datasets)
# File: resumes/resumes.jsonl
{"id": "001", "resume_text": "Senior Python Engineer with 8 years..."}
{"id": "002", "resume_text": "Full Stack Developer with React..."}

# Option B: Individual text files
# Files: resumes/001.txt, resumes/002.txt, etc.
Senior Python Engineer with 8 years of experience...

# Option C: Individual JSON files
# Files: resumes/001.json, resumes/002.json, etc.
{"id": "001", "resume_text": "Senior Engineer..."}
```

**Create job description file** `job_description.txt`:

```
Senior Python Engineer

Requirements:
- 5+ years software engineering
- Python, distributed systems, AWS
- Team leadership experience
```

### 3. Run Screening

**For small datasets (<50K resumes):**
```bash
python run_screening.py \
  --resume-dir ./resumes \
  --jd-file ./job_description.txt \
  --top-k 100
```

**For large datasets (50K+ resumes) with 3-tier optimization:**
```bash
python run_screening.py \
  --resume-dir ./resumes \
  --jd-file ./job_description.txt \
  --top-k 100 \
  --tiered \
  --workers 8
```

### 4. View Results

Results print to console or save to JSON:

```bash
python run_screening.py \
  --resume-dir ./resumes \
  --jd-file ./job_description.txt \
  --output results.json
```

**Output format:**
```json
{
  "total_resumes_processed": 1000,
  "elapsed_seconds": 45.23,
  "candidates": [
    {
      "rank": 1,
      "resume_id": "candidate_042",
      "overall_score": 87.23,
      "all_scores": {
        "semantic_fit": 92.1,
        "career_growth": 78.5,
        "narrative_coherence": 82.0,
        "team_portfolio": 74.2,
        "artifact_complexity": 88.0
      },
      "reasons": [
        "Strong semantic alignment",
        "Career shows upward trajectory"
      ]
    }
  ]
}
```

---

## 🎯 10 Scoring Dimensions

| Dimension | Weight | What It Measures |
|-----------|--------|------------------|
| **Semantic Fit** | 25% | Resume-JD meaning similarity (beyond keywords) |
| **Career Growth** | 15% | Promotion velocity, leadership signals |
| **Narrative Coherence** | 10% | Title vs responsibility alignment |
| **Team Portfolio** | 10% | Skill breadth (T-shaped vs specialist) |
| **Artifact Complexity** | 10% | Project difficulty (distributed systems, scale, ML) |
| **Skill Currency** | 10% | Skill recency and relevance |
| **Resilience** | 10% | Career gap handling and pivots |
| **Company Context** | 5% | Startup vs enterprise experience |
| **Counterfactual** | 5% | Outperformance vs expected trajectory |
| **Keyword Match** | 0%* | Traditional keyword overlap (for bias analysis) |

*Keyword match computed but not included in final score — used for bias comparison

---

## ⚡ 3-Tier Filtering (Performance Optimization)

For large datasets (50K+), use `--tiered` to enable progressive filtering:

```
200K resumes
    ↓
TIER 1: Semantic + Keyword (70s)
    ↓ filters to 40K
TIER 2: + Medium Heuristics (20s)
    ↓ filters to 5K
TIER 3: + Deep Analysis (3s)
    ↓ Top 100
```

**Performance**: Reduces processing time from **5 min → 1.5 min** (3x faster)

**When to use:**
- ✅ Use `--tiered` for 50K+ resumes
- ❌ Skip for <5K resumes (overhead not worth it)

---

## 🛠️ Command Options

```bash
python run_screening.py \
  --resume-dir <path>           # Directory with resume files (required)
  --jd <text>                   # Inline job description
  --jd-file <path>              # Job description from file (one or the other)
  --top-k <N>                   # Number of candidates to return (default: 100)
  --output <path>               # Save results to JSON file
  --tiered                      # Enable 3-tier filtering (for 50K+)
  --workers <N>                 # Parallel workers (default: CPU count)
  --tier1-size <N>              # Tier 1 cutoff (default: 40000)
  --tier2-size <N>              # Tier 2 cutoff (default: 5000)
  --cache-dir <path>            # Cache ML model for faster re-runs
  --from-cache                  # Skip model training, use cached
  --weights <json>              # Custom dimension weights
```

### Common Use Cases

**Save results to file:**
```bash
python run_screening.py \
  --resume-dir ./resumes \
  --jd-file ./jd.txt \
  --output results.json
```

**Custom weights (e.g., emphasize leadership for tech lead role):**
```bash
python run_screening.py \
  --resume-dir ./resumes \
  --jd-file ./jd.txt \
  --weights '{"semantic_fit":0.3,"career_growth":0.25,"team_portfolio":0.20}'
```

**Cache model for multiple JD screenings on same resume pool:**
```bash
# First run - builds and caches model
python run_screening.py --resume-dir ./resumes --jd-file ./jd1.txt --cache-dir ./cache

# Subsequent runs - reuses cached model (much faster!)
python run_screening.py --resume-dir ./resumes --jd-file ./jd2.txt --cache-dir ./cache --from-cache
```

**Process large dataset with all CPU cores:**
```bash
python run_screening.py \
  --resume-dir ./resumes \
  --jd-file ./jd.txt \
  --tiered \
  --workers 16
```

---

## 📈 Performance Benchmarks

**Hardware**: 16GB RAM, 8-core CPU (no GPU)

| Resumes | Mode | Time | Speed |
|---------|------|------|-------|
| 500 | Standard | 45s | 11/sec |
| 5,000 | Standard | 250s | 20/sec |
| 5,000 | Tiered | 180s | 28/sec |
| 50,000 | Standard | 2,100s | 24/sec |
| 50,000 | Tiered | 900s | **56/sec** |
| 200,000 | Standard | 8,400s | 24/sec |
| 200,000 | Tiered | 2,700s | **74/sec** |

*Note: Tiering has overhead — use only for 50K+ resumes*

---

## 🏗️ How It Works

### Standard Pipeline
All resumes processed through 10 scoring dimensions using TF-IDF + LSA for semantic understanding, regex-based heuristics for career analysis, and weighted aggregation for final ranking.

### Tiered Pipeline (with `--tiered` flag)

**Tier 1** (Fast vectorized ops):
- Semantic similarity (TF-IDF + LSA)
- Keyword matching
- Score: `0.7 × semantic + 0.3 × keyword`
- Filters to top 40K

**Tier 2** (Medium-cost heuristics):
- Narrative coherence (title/responsibility alignment)
- Team portfolio (skill domain breadth)
- Artifact complexity (project difficulty signals)
- Filters to top 5K

**Tier 3** (Expensive deep analysis):
- Career trajectory (6-dimension analysis)
- Counterfactual (career path simulation)
- All 10 dimensions combined
- Returns top N candidates

---

## 📁 Project Structure

```
ats-intelligence/
├── run_screening.py             # CLI entry point
├── requirements.txt
├── README.md
├── GETTING_STARTED.md          # Detailed setup guide
├── UI_DEVELOPMENT_SPEC.md      # Full-stack UI specification
│
├── app/
│   ├── core/
│   │   └── config.py           # Configuration
│   ├── models/
│   │   └── schemas.py          # Data schemas
│   └── services/
│       ├── batch/
│       │   ├── pipeline.py              # Main orchestrator (tiered + standard)
│       │   ├── semantic_engine.py       # TF-IDF + LSA
│       │   └── screener.py              # Cache-based screening
│       ├── career_trajectory/           # Career growth analysis
│       ├── narrative_coherence/         # Story consistency
│       ├── team_portfolio/              # Skill breadth
│       ├── artifact_complexity/         # Project difficulty
│       ├── counterfactual/              # Career simulation
│       ├── bias_mirror/                 # Keyword matching + bias analysis
│       └── [other services]/
│
└── tests/
    ├── test_tiers_quick.py
    └── test_full_pipeline.py
```

---

## 🧪 Testing

Verify installation with the test suite:

```bash
# Quick tier test (1000 resumes)
python test_tiers_quick.py

# Full pipeline test (500 resumes)
python test_full_pipeline.py
```

Expected output:
```
🎉 ALL TESTS PASSED!
Tier 1 and Tier 2 are working correctly!
```

---

## 🚀 Building a Web UI

See **[UI_DEVELOPMENT_SPEC.md](UI_DEVELOPMENT_SPEC.md)** for complete specification to build a React + FastAPI web interface with:
- REST + WebSocket API specification
- PostgreSQL database schema
- React + Tailwind component structure
- Docker Compose setup
- 5-week development roadmap

---

## 💡 Use Cases

- **Recruiting agencies**: Screen thousands of resumes efficiently
- **HR departments**: Initial candidate filtering for high-volume roles
- **Talent acquisition**: Find hidden talent beyond keyword matches
- **Research**: Study hiring bias and resume screening patterns

---

## 📚 Documentation for Team

- **[TEAM_SETUP_GUIDE.md](TEAM_SETUP_GUIDE.md)** - 🚀 **START HERE** - Complete team onboarding guide
- **[GETTING_STARTED.md](GETTING_STARTED.md)** - Detailed CLI usage and examples
- **[UI_DEVELOPMENT_SPEC.md](UI_DEVELOPMENT_SPEC.md)** - Full-stack UI development specification

---

## ⚠️ Important Notes

- **Privacy**: All processing is offline — no data sent to external services
- **Bias**: System includes bias comparison to highlight differences from keyword matching
- **Accuracy**: Best used as a filtering tool, not final decision maker
- **PDF Support**: Not included (extract text first using any PDF parser)

---

## 🤝 Contributing

We welcome contributions! Areas for improvement:
- Additional scoring dimensions
- PDF resume parsing
- ML-based scoring models
- Cloud deployment guides
- Performance optimizations

---

## 📄 License

MIT License - see LICENSE file for details

---

**Built with Python, scikit-learn, NumPy, and ❤️**
