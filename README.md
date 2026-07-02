# ATS Intelligence Engine

AI-powered resume screening system for ranking candidates against a job description. The project is designed for hackathon-style candidate datasets and produces ranked CSV and Excel outputs with candidate-specific reasoning.

The engine uses fast, local scoring methods such as TF-IDF, LSA, rule-based career analysis, behavioral signals, honeypot detection, and tiered filtering. It does not require a GPU, external APIs, or internet access during screening.

## Key Features

- Streamlit web app for uploading candidate datasets and job descriptions.
- CLI submission generator for repeatable batch runs.
- Supports JSON and JSONL candidate files.
- Supports text, DOCX, and PDF job descriptions in the Streamlit app.
- Generates top candidate rankings with score and reasoning.
- Exports CSV and Excel files.
- Filters suspicious or impossible candidate profiles using honeypot detection.
- Uses behavioral signals such as response rate, notice period, profile completeness, and relocation willingness.
- Optimized path for large datasets using fast prefiltering and tiered scoring.

## Project Structure

```text
ats-intelligence/
+-- app_streamlit.py                  # Streamlit web application
+-- generate_submission.py            # CLI generator for CSV/XLSX submissions
+-- requirements.txt                  # Python dependencies
+-- runtime.txt                       # Python runtime for Streamlit Cloud
+-- .streamlit/
|   +-- config.toml                   # Streamlit configuration
+-- app/
|   +-- core/
|   +-- models/
|   +-- services/
|       +-- batch/
|       |   +-- pipeline.py           # Main ranking pipeline
|       |   +-- semantic_engine.py    # TF-IDF + LSA semantic scoring
|       |   +-- screener.py
|       +-- behavioral_signals/
|       +-- bias_mirror/
|       +-- career_trajectory/
|       +-- narrative_coherence/
|       +-- team_portfolio/
|       +-- artifact_complexity/
|       +-- counterfactual/
|       +-- csv_writer.py
|       +-- honeypot_detector.py
|       +-- reasoning_generator.py
+-- docs/
```

## Installation

Use Python 3.11 for best compatibility with Streamlit Community Cloud and the pinned dependencies.

```bash
git clone <repository-url>
cd ats-intelligence-main
python -m venv .venv
```

Activate the virtual environment.

Windows:

```bash
.venv\Scripts\activate
```

macOS or Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run the Streamlit App Locally

```bash
streamlit run app_streamlit.py
```

Open the local URL shown in the terminal, usually:

```text
http://localhost:8501
```

## Streamlit App Usage

1. Upload a candidate file in JSON or JSONL format.
2. Upload a job description file or paste the job description text.
3. Select the number of top candidates to rank.
4. Click the run button.
5. Download the generated CSV or Excel output.

## Candidate Input Format

JSONL is recommended for large datasets because it streams cleanly and is easier to process at scale.

Each line should contain one candidate record:

```json
{"candidate_id":"CAND_000001","profile":{"current_title":"Senior AI Engineer","current_company":"ExampleTech","current_industry":"Technology","location":"Pune","years_of_experience":7},"career_history":[{"title":"Senior AI Engineer","company":"ExampleTech","description":"Built retrieval and ranking systems for production search.","duration_months":36}],"skills":[{"name":"Python","proficiency":"expert","duration_months":72},{"name":"Machine Learning","proficiency":"advanced","duration_months":60}],"redrob_signals":{"recruiter_response_rate":0.72,"notice_period_days":30,"open_to_work_flag":true,"willing_to_relocate":true,"profile_completeness_score":91,"github_activity_score":78}}
```

Required fields:

- `candidate_id`
- `profile`
- `career_history`
- `skills`

Recommended fields:

- `redrob_signals`
- `education`
- role descriptions in `career_history`
- skill proficiency and duration

## Job Description Input

The job description can be provided as:

- pasted text
- `.txt`
- `.docx`
- `.pdf`

Example:

```text
Senior AI Engineer

Requirements:
- 5-9 years of experience
- Strong Python, machine learning, embeddings, retrieval, vector database, NLP, and LLM experience
- Experience with ranking, search, APIs, monitoring, and scalable backend systems
- Preferred locations: Pune, Noida, Bangalore, Hyderabad, Mumbai, or Delhi
```

## CLI Usage

Use the CLI when you want repeatable local runs or direct file output.

```bash
python generate_submission.py ^
  --candidates path\to\candidates.jsonl ^
  --jd path\to\job_description.txt ^
  --output ranking_results.csv ^
  --excel-output ranking_results.xlsx ^
  --workers 8
```

On macOS or Linux:

```bash
python generate_submission.py \
  --candidates path/to/candidates.jsonl \
  --jd path/to/job_description.txt \
  --output ranking_results.csv \
  --excel-output ranking_results.xlsx \
  --workers 8
```

## Output Format

The CSV and Excel files use the hackathon submission format:

```text
candidate_id,rank,score,reasoning
```

Example:

```csv
candidate_id,rank,score,reasoning
CAND_000123,1,0.8421,"7.0 yrs as Senior AI Engineer at ExampleTech; matched skills: Python (expert, 6y), Machine Learning (advanced, 5y); short notice period (30 days)."
```

## Scoring Dimensions

| Dimension | Purpose |
| --- | --- |
| Semantic Fit | Measures resume-to-JD meaning similarity using TF-IDF and LSA. |
| Career Growth | Evaluates progression, seniority, and career movement. |
| Company Context | Adds context from company type and background. |
| Skill Currency | Rewards relevant and current skills. |
| Resilience | Looks at gaps, pivots, and career stability. |
| Narrative Coherence | Checks whether titles, responsibilities, and experience align. |
| Team Portfolio | Measures breadth of skill portfolio. |
| Artifact Complexity | Detects evidence of complex projects and systems. |
| Counterfactual | Compares candidate trajectory against expected patterns. |
| Behavioral Signals | Applies multiplier based on availability and engagement signals. |

## Performance Design

The app is optimized for large candidate files using:

- TF-IDF prefiltering before expensive scoring.
- A single temporary `resumes.jsonl` file instead of thousands of small text files.
- Tiered scoring that applies heavier analysis only to shortlisted candidates.
- Parallel workers for medium and deep analysis stages.
- Optional `orjson` for faster JSON parsing.

For large datasets, the expected flow is:

```text
Full dataset
-> Fast TF-IDF prefilter
-> Tier 1 semantic scoring
-> Tier 2 medium-cost heuristics
-> Tier 3 deep analysis
-> Top ranked candidates
```

## Streamlit Community Cloud Deployment

1. Push the repository to GitHub.
2. Ensure these files are present at the repository root:
   - `app_streamlit.py`
   - `requirements.txt`
   - `runtime.txt`
   - `.streamlit/config.toml`
   - `app/`
3. In Streamlit Community Cloud, create a new app.
4. Select the repository and branch.
5. Set the main file path to:

```text
app_streamlit.py
```

6. Deploy the app.

The included `runtime.txt` pins Python 3.11:

```text
python-3.11
```

## Streamlit Cloud Troubleshooting

### App fails while installing dependencies

Use the pinned `requirements.txt` included in this repository. It pins versions with stable wheels for Python 3.11.

### App cannot import local modules

Confirm that `app_streamlit.py` is at the repository root and the `app/` directory is also committed.

### Upload fails for large files

Check `.streamlit/config.toml`:

```toml
[server]
maxUploadSize = 500
```

If your dataset is larger than 500 MB, reduce the dataset size, split it, or increase the limit if your deployment environment allows it.

### App runs locally but crashes on Cloud

Check the Streamlit Cloud logs for the first traceback. Common causes are:

- missing files not committed to GitHub
- incorrect main file path
- dependency installation failure
- Python version mismatch
- file upload larger than the configured limit
- memory pressure from very large datasets

## Local Testing

Run syntax checks:

```bash
python -m py_compile app_streamlit.py generate_submission.py app/services/batch/pipeline.py app/services/reasoning_generator.py
```

Run a quick CSV generation test:

```bash
python test_csv_generation.py
```

Run pipeline tests:

```bash
python test_tiers_quick.py
python test_full_pipeline.py
```

## Notes and Limitations

- This tool is intended for screening support, not final hiring decisions.
- Scores should be reviewed with human judgment.
- Candidate data is processed locally inside the app runtime.
- No external AI API is required.
- PDF job descriptions are supported, but candidate resumes should be uploaded as structured JSON or JSONL.

## License

MIT License. See `LICENSE` for details.
