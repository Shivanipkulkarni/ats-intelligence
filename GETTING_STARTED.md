# Getting Started with ATS Intelligence Engine

## Quick Start Guide

### Step 1: Install Dependencies

```bash
cd C:\Users\USER\OneDrive\Desktop\MyCodes\ats-intelligence
pip install -r requirements.txt
```

---

## Step 2: Prepare Your Resumes

### Option A: JSONL Format (Recommended for Large Batches)

Create a single file: `resumes/resumes.jsonl`

Each line is a JSON object:
```jsonl
{"id": "001", "resume_text": "John Doe - Senior Software Engineer with 8 years of Python experience..."}
{"id": "002", "resume_text": "Jane Smith - Full Stack Developer with React and Node.js expertise..."}
{"id": "003", "resume_text": "Mike Johnson - Data Scientist with ML and AI background..."}
```

### Option B: Individual JSON Files

Create separate files in `resumes/` folder:

**File: `resumes/001.json`**
```json
{
  "id": "001",
  "resume_text": "John Doe - Senior Software Engineer with 8 years of Python experience..."
}
```

**File: `resumes/002.json`**
```json
{
  "id": "002",
  "resume_text": "Jane Smith - Full Stack Developer with React and Node.js expertise..."
}
```

### Option C: Plain Text Files

Create `.txt` files in `resumes/` folder:

**File: `resumes/001.txt`**
```
John Doe - Senior Software Engineer with 8 years of Python experience...
```

**File: `resumes/002.txt`**
```
Jane Smith - Full Stack Developer with React and Node.js expertise...
```

---

## Step 3: Prepare Your Job Description

### Option A: Create a JD File

**File: `job_description.txt`**
```
Senior Python Engineer

Requirements:
- 5+ years of software engineering experience
- Strong Python expertise and system design skills
- Experience with distributed systems and microservices
- Cloud platforms (AWS, GCP, or Azure)
- Container orchestration (Docker, Kubernetes)
- Team leadership and mentoring experience

Nice to have:
- Machine learning or data engineering experience
- Experience at high-growth startups
```

### Option B: Use Inline JD (for short descriptions)

Just pass it directly in the command line.

---

## Step 4: Run the Screening

### Basic Usage (Standard Mode)

```bash
python run_screening.py \
  --resume-dir ./resumes \
  --jd-file ./job_description.txt \
  --top-k 100
```

### Fast Mode (Tiered Filtering - Recommended for 50K+ resumes)

```bash
python run_screening.py \
  --resume-dir ./resumes \
  --jd-file ./job_description.txt \
  --top-k 100 \
  --tiered \
  --workers 8
```

### Save Results to File

```bash
python run_screening.py \
  --resume-dir ./resumes \
  --jd-file ./job_description.txt \
  --top-k 50 \
  --output ./results.json \
  --tiered
```

### With Inline Job Description

```bash
python run_screening.py \
  --resume-dir ./resumes \
  --jd "Senior Python Developer with AWS and team leadership experience" \
  --top-k 100 \
  --tiered
```

---

## Step 5: View Results

### Console Output

When run without `--output`, results print to console:

```
================================================================================
SCREENING RESULTS
================================================================================
Processed 1000 resumes in 45.23s

Tiered Processing Breakdown:
  Tier 1 (Semantic + Keyword): 15.34s → 400 candidates
  Tier 2 (Medium Heuristics):  8.12s → 100 candidates
  Tier 3 (Deep Analysis):      2.45s → 50 candidates

Top 100 Candidates:
--------------------------------------------------------------------------------
  #  1 | resume_042                            | Score: 87.23
  #  2 | resume_156                            | Score: 85.91
  #  3 | resume_089                            | Score: 84.52
  ...
```

### JSON Output File

With `--output results.json`, you get a detailed JSON:

```json
{
  "job_title": "",
  "top_k": 100,
  "total_resumes_processed": 1000,
  "elapsed_seconds": 45.23,
  "tier_stats": {
    "tier1_elapsed": 15.34,
    "tier2_elapsed": 8.12,
    "tier3_elapsed": 2.45,
    "tier1_cutoff": 400,
    "tier2_cutoff": 100
  },
  "candidates": [
    {
      "rank": 1,
      "resume_id": "resume_042",
      "overall_score": 87.23,
      "all_scores": {
        "semantic_fit": 92.1,
        "career_growth": 78.5,
        "company_context": 65.0,
        "skill_currency": 60.0,
        "resilience": 65.0,
        "narrative_coherence": 82.0,
        "team_portfolio": 74.2,
        "artifact_complexity": 88.0,
        "counterfactual": 71.5,
        "keyword_match": 68.4
      },
      "reasons": [
        "Strong semantic alignment despite possible keyword differences.",
        "Career shows continuous upward trajectory."
      ]
    }
  ]
}
```

---

## Complete Example Workflow

### 1. Create a project structure:

```
my_screening_project/
├── resumes/
│   └── resumes.jsonl
├── job_description.txt
└── results/
```

### 2. Add resumes to `resumes/resumes.jsonl`:

```jsonl
{"id": "candidate_001", "resume_text": "Senior Software Engineer at Google with 10 years experience in distributed systems, Python, Kubernetes, and team leadership. Built scalable microservices serving 100M users..."}
{"id": "candidate_002", "resume_text": "Full Stack Developer with 5 years building React and Node.js applications. Experience with AWS, Docker, CI/CD pipelines..."}
```

### 3. Create `job_description.txt`:

```
Senior Backend Engineer

We're looking for an experienced engineer to lead our backend team.

Requirements:
- 7+ years of software engineering
- Python or Java expertise
- Distributed systems and microservices
- AWS or GCP
- Team leadership
```

### 4. Run screening:

```bash
cd C:\Users\USER\OneDrive\Desktop\MyCodes\ats-intelligence

python run_screening.py \
  --resume-dir C:\path\to\my_screening_project\resumes \
  --jd-file C:\path\to\my_screening_project\job_description.txt \
  --top-k 50 \
  --output C:\path\to\my_screening_project\results\screening_results.json \
  --tiered \
  --workers 8 \
  --cache-dir C:\path\to\my_screening_project\cache
```

### 5. View results:

```bash
# Open JSON file
notepad C:\path\to\my_screening_project\results\screening_results.json

# Or use Python to pretty-print
python -m json.tool C:\path\to\my_screening_project\results\screening_results.json
```

---

## Advanced Options

### Custom Dimension Weights

Emphasize different aspects based on your role:

```bash
# For tech lead role - emphasize career growth and leadership
python run_screening.py \
  --resume-dir ./resumes \
  --jd-file ./jd.txt \
  --weights '{"semantic_fit":0.3,"career_growth":0.25,"team_portfolio":0.20}'

# For specialist role - emphasize semantic fit and skills
python run_screening.py \
  --resume-dir ./resumes \
  --jd-file ./jd.txt \
  --weights '{"semantic_fit":0.5,"artifact_complexity":0.25}'
```

### Custom Tier Sizes

For very large datasets:

```bash
python run_screening.py \
  --resume-dir ./resumes \
  --jd-file ./jd.txt \
  --tiered \
  --tier1-size 50000 \
  --tier2-size 8000 \
  --top-k 200
```

### Use Cached Model

Speed up subsequent runs with the same resume pool:

```bash
# First run - builds and saves model
python run_screening.py \
  --resume-dir ./resumes \
  --jd-file ./jd1.txt \
  --cache-dir ./cache \
  --tiered

# Second run - reuses model (faster!)
python run_screening.py \
  --resume-dir ./resumes \
  --jd-file ./jd2.txt \
  --cache-dir ./cache \
  --from-cache \
  --tiered
```

---

## Common Scenarios

### Scenario 1: Screening 100 Resumes for Startup

```bash
python run_screening.py \
  --resume-dir ./resumes \
  --jd "Full Stack Engineer with React and Python" \
  --top-k 20
```
*(No need for --tiered with small datasets)*

### Scenario 2: Screening 50K Resumes for Tech Company

```bash
python run_screening.py \
  --resume-dir ./resumes \
  --jd-file ./senior_engineer_jd.txt \
  --top-k 100 \
  --tiered \
  --workers 8 \
  --cache-dir ./cache \
  --output ./results_senior_engineer.json
```

### Scenario 3: Comparing Multiple JDs on Same Pool

```bash
# Build model once
python run_screening.py \
  --resume-dir ./resumes \
  --jd-file ./jd_backend.txt \
  --cache-dir ./cache \
  --tiered \
  --output ./results_backend.json

# Reuse model for other JDs (much faster)
python run_screening.py \
  --resume-dir ./resumes \
  --jd-file ./jd_frontend.txt \
  --cache-dir ./cache \
  --from-cache \
  --tiered \
  --output ./results_frontend.json

python run_screening.py \
  --resume-dir ./resumes \
  --jd-file ./jd_devops.txt \
  --cache-dir ./cache \
  --from-cache \
  --tiered \
  --output ./results_devops.json
```

---

## Troubleshooting

### Issue: "No resumes found in directory"

**Solution**: Check that:
- Resume files are in the correct format (`.jsonl`, `.json`, or `.txt`)
- Path to `--resume-dir` is correct
- Files are not empty

### Issue: "Slow performance on small datasets"

**Solution**: Don't use `--tiered` for <5,000 resumes. Tiering adds overhead.

```bash
# Better for small datasets:
python run_screening.py --resume-dir ./resumes --jd-file ./jd.txt
```

### Issue: "Out of memory error"

**Solution**: 
1. Use `--tiered` mode (reduces memory usage)
2. Reduce `--max-features` parameter
3. Process in batches

---

## Next Steps

1. ✅ Install dependencies
2. ✅ Prepare your resumes folder
3. ✅ Create job description file
4. ✅ Run your first screening
5. 📊 Analyze results and iterate

**Need help?** Check `README.md` for detailed documentation on all scoring dimensions and architecture details.
