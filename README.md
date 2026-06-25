# ATS Intelligence Engine — Batch Resume Screener

Offline resume screening engine that shortlists the top N candidates from a large resume pool using **10 scoring dimensions** — combining semantic understanding (TF-IDF + LSA), career trajectory analysis, skill recency, and bias comparison against keyword matching.

Designed to run on **16GB RAM, no GPU, no internet**. Targets **200K resumes in under 5 minutes** on an 8-core CPU.

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Basic run
python run_screening.py \
  --resume-dir ./resumes \
  --jd "Senior Python developer with AWS and team leadership" \
  --top-k 100

# With a JD file
python run_screening.py \
  --resume-dir ./resumes \
  --jd-file ./job_description.txt \
  --top-k 50

# Save results to file
python run_screening.py \
  --resume-dir ./resumes \
  --jd "Data Scientist" \
  --output ./results.json

# Use all CPU cores for parallel processing
python run_screening.py \
  --resume-dir ./resumes \
  --jd "DevOps engineer" \
  --workers 8

# Custom dimension weights
python run_screening.py \
  --resume-dir ./resumes \
  --jd "ML Engineer" \
  --weights '{"semantic_fit":0.4,"career_growth":0.2,"team_portfolio":0.2}'

# Cache fitted model for faster re-runs
python run_screening.py \
  --resume-dir ./resumes \
  --jd-file ./jd.txt \
  --cache-dir ./cache
```

---

## Input Formats

Resumes go in a single directory (`--resume-dir`). Supported formats:

### JSONL (fastest for bulk — single file)
File: `resumes/resumes.jsonl`
```jsonl
{"id": "001", "resume_text": "Senior Engineer with 8 years Python..."}
{"id": "002", "resume_text": "Data Scientist with ML experience..."}
```

### Individual JSON files
File: `resumes/001.json`
```json
{"id": "001", "resume_text": "Senior Engineer with 8 years Python..."}
```

### Individual TXT files
File: `resumes/001.txt`
```
Senior Engineer with 8 years Python experience...
```

---

## 10 Scoring Dimensions

| # | Dimension | Score Range | What It Measures | Method |
|---|-----------|-------------|------------------|--------|
| 1 | **Semantic Fit** | 0–100 | Resume-JD meaning similarity (beyond keyword overlap) | TF-IDF + LSA (dense vectors) |
| 2 | **Career Growth** | 0–100 | Promotion velocity, leadership, ownership signals | Regex/heuristic from parsed roles |
| 3 | **Company Context** | Fixed 65 | Neutral default (requires structured company data) | — |
| 4 | **Skill Currency** | Fixed 60 | Neutral default (requires structured role history) | — |
| 5 | **Resilience** | Fixed 65 | Neutral default (requires structured role dates) | — |
| 6 | **Narrative Coherence** | 0–100 | Title vs responsibility alignment, logical progression | Title-rank cross-check with signal analysis |
| 7 | **Team Portfolio** | 0–100 | Breadth of skill domains (T-shaped vs specialist) | Skill categorization into 6 domains |
| 8 | **Artifact Complexity** | 0–100 | Project difficulty signals (distributed systems, scale, ML) | Weighted regex on responsibility text |
| 9 | **Counterfactual** | 0–100 | Outperformance vs expected industry trajectory | Seniority simulation vs actual path |
| 10 | **Keyword Match** | 0–100 | Traditional keyword overlap (for bias comparison) | Exact term + bigram matching |

Default weights: Semantic 25%, Career 15%, Context 5%, Currency 10%, Resilience 10%, Narrative 10%, Portfolio 10%, Complexity 10%, Counterfactual 5%.

---

## Architecture

```
run_screening.py (CLI)
  │
  └── BatchPipeline (services/batch/pipeline.py)
        │
        ├── BatchSemanticEngine (services/batch/semantic_engine.py)
        │     ├── TfidfVectorizer → sparse TF-IDF matrix
        │     └── TruncatedSVD → dense LSA vectors (128-dim)
        │
        ├── Career Trajectory (services/career_trajectory/)
        │     ├── extractor.py — Regex role parser from text
        │     ├── analyzer.py — 6-dimension career analysis
        │     └── scorer.py — Aggregation → career_growth_score
        │
        ├── Narrative Coherence (services/narrative_coherence/)
        │     └── scorer.py — Title/description alignment check
        │
        ├── Team Portfolio (services/team_portfolio/)
        │     └── scorer.py — Skill domain breadth analysis
        │
        ├── Artifact Complexity (services/artifact_complexity/)
        │     └── scorer.py — Project difficulty signal detection
        │
        ├── Counterfactual (services/counterfactual/)
        │     └── scorer.py — Career path simulation
        │
        └── Bias Mirror (services/bias_mirror/)
              └── scorer.py — Keyword matcher + ranking comparison
```

### Data Flow

1. **Load** → reads all resumes from directory (JSON/JSONL/TXT)
2. **Fit** → TF-IDF + LSA trained on entire resume corpus
3. **Encode** → JD vectorized using same model
4. **Semantic score** → cosine similarity of JD vs each resume's LSA vector
5. **Heuristic scores** → roles parsed once per resume → all 5 analysis dimensions computed
6. **Keyword score** → traditional term overlap (for bias comparison)
7. **Rank** → weighted aggregation → top N sorted by overall score
8. **Bias report** → LSA ranking vs keyword ranking side by side

---

## CLI Reference

```
positional arguments:
  --resume-dir DIR      Directory containing resume JSON/TXT/JSONL files
  --jd TEXT             Job description text (inline)
  --jd-file PATH        Path to file containing job description text

optional arguments:
  --top-k N             Number of top candidates to return (default: 100)
  --output PATH         Output JSON file path (optional, prints to stdout)
  --cache-dir DIR       Save/load fitted TF-IDF + LSA model
  --from-cache          Skip fitting, load from cache-dir
  --workers N           Number of parallel workers (default: CPU count)
  --n-components N      LSA dimensions (default: 128)
  --max-features N      Max TF-IDF vocabulary size (default: 10000)
  --weights JSON        Custom dimension weights JSON, e.g. '{"semantic_fit":0.4}'
  --verbose             Print detailed progress
```

---

## Output Format

```json
{
  "job_title": "",
  "top_k": 100,
  "total_resumes_processed": 200000,
  "elapsed_seconds": 287.4,
  "candidates": [
    {
      "rank": 1,
      "resume_id": "candidate_042",
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
        "Career shows continuous upward trajectory.",
        "Broad skill portfolio across 4 domains (T-shaped profile).",
        "High-complexity projects detected: distributed systems, scale, or infrastructure work."
      ]
    }
  ],
  "lsa_ranking": [...],
  "keyword_ranking": [...],
  "bias_comparison": {
    "summary": {
      "overlap_count": 65,
      "overlap_pct": 65.0,
      "lsa_only_count": 35,
      "keyword_only_count": 35,
      "avg_rank_shift": 4.2
    }
  }
}
```

---

## Performance Targets

Hardware: 16GB RAM, 8 CPU cores, SSD. No GPU, no internet.

| Operation | ~Throughput | 200K Resumes |
|-----------|-------------|--------------|
| File loading (JSONL) | ~20K/sec | ~10s |
| TF-IDF fit + transform | ~10K docs/sec | ~30s |
| LSA fit + transform | ~5K docs/sec | ~45s |
| Heuristic signals (1 core) | ~170 docs/sec | ~20 min |
| Heuristic signals (8 cores) | ~1,300 docs/sec | ~2.5 min |
| Keyword matching (8 cores) | ~8K docs/sec | ~25s |
| Ranking | ~200K/sec | ~1s |
| **Total (8 cores)** | — | **~4-5 min** |

Optimize for speed:
- Use a single `resumes.jsonl` file (not individual JSON files)
- Use `--workers N` with N = CPU count
- Use `--cache-dir` to persist the fitted model for subsequent runs with different JDs

---

## File Map

```
ats-intelligence/
├── run_screening.py              CLI entry point
├── requirements.txt              Python dependencies
├── .env                          Environment variables
├── .gitignore
├── README.md
│
├── app/
│   ├── core/
│   │   └── config.py             Settings (LSA dims, features, env)
│   │
│   ├── models/
│   │   └── schemas.py            Pydantic models for all inputs/outputs
│   │
│   └── services/
│       ├── batch/
│       │   ├── semantic_engine.py    TF-IDF + LSA vectorization
│       │   ├── pipeline.py           Main orchestrator + scoring
│       │   └── screener.py           Cache-based fast re-scoring
│       │
│       ├── career_trajectory/        Role parsing + 6-dimension career analysis
│       ├── narrative_coherence/      Career story consistency check
│       ├── team_portfolio/           Skill domain breadth scoring
│       ├── artifact_complexity/      Project difficulty inference
│       ├── counterfactual/           Career path simulation
│       ├── bias_mirror/              Keyword matcher + comparison report
│       │
│       ├── semantic_fit/             Text preprocessing + embedding (offline-capable)
│       ├── company_context/          Company classification (available for future use)
│       ├── skill_decay/              Skill freshness tracking (available for future use)
│       └── crisis_response/          Gap detection (available for future use)
```

---

## Dependencies

- `scikit-learn` — TF-IDF vectorization, TruncatedSVD (LSA)
- `numpy` — array operations, cosine similarity
- `scipy` — sparse matrix support
- `joblib` — model serialization
- `pydantic` + `pydantic-settings` — configuration and data models
- `python-dotenv` — environment file loading

No GPU required. No internet required. No deep learning frameworks.

---

## FAQ

**Q: Can I add structured role/company data for more accurate scoring?**
A: Yes. The career trajectory, company context, skill decay, and crisis response modules all accept structured input via their respective scorer functions. The batch pipeline currently uses text-based heuristic parsing, but the modules are designed for structured data.

**Q: How is this different from keyword matching?**
A: LSA vectors capture latent semantic relationships (e.g., "designed microservices" and "architected distributed systems" match), while keyword matching only counts exact term overlap. The bias comparison module quantifies the difference.

**Q: Can I run this on resume PDFs?**
A: Not directly. Extract text from PDFs first (using any tool) and save as JSON/TXT. PDF parsing is too slow for 200K in 5 minutes.
