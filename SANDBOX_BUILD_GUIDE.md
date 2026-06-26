# 🚀 Sandbox Build Guide for Teammates

## What Needs to Be Built

A simple web demo that lets organizers test our ranking system on small datasets.

**Time Required:** 2-4 hours
**Difficulty:** Easy (just a web wrapper around existing code)

---

## Requirements (from Submission Spec)

The sandbox must:
1. Accept small candidate sample (≤100 candidates) as input
2. Run ranking system end-to-end
3. Produce a ranked CSV output
4. Complete in <5 minutes on CPU

**Acceptable platforms:**
- HuggingFace Spaces (Recommended - Free)
- Streamlit Cloud (Free)
- Google Colab (Simplest)
- Replit (Free)

---

## Option 1: Streamlit App (Recommended - 2 hours)

### File to Create: `app_streamlit.py`

```python
import streamlit as st
import json
import tempfile
import os
from generate_submission import load_candidates_jsonl, save_temp_resumes
from app.services.batch.pipeline import BatchPipeline
from app.services.reasoning_generator import ReasoningGenerator, parse_jd_requirements
from app.services.csv_writer import write_submission_csv
from app.services.behavioral_signals.scorer import apply_behavioral_multiplier
from app.services.honeypot_detector import HoneypotDetector

st.title("🎯 ATS Intelligence Engine - Demo")
st.markdown("Intelligent resume ranking with 10 scoring dimensions")

# Sidebar
st.sidebar.header("About")
st.sidebar.markdown("""
This demo ranks candidates using:
- Semantic similarity (TF-IDF + LSA)
- Career trajectory analysis
- Behavioral signals
- Honeypot detection
""")

# File upload
uploaded_file = st.file_uploader(
    "Upload candidates.jsonl (max 100 candidates)", 
    type=['jsonl']
)

# Job description
jd_text = st.text_area(
    "Job Description", 
    height=200,
    placeholder="Paste job description here..."
)

# Number of results
top_k = st.slider("Number of candidates to rank", 10, 100, 50)

# Run button
if st.button("Run Ranking", type="primary"):
    if not uploaded_file or not jd_text:
        st.error("Please provide both candidates file and job description")
    else:
        with st.spinner("Processing..."):
            try:
                # Save uploaded file
                with tempfile.NamedTemporaryFile(
                    delete=False, 
                    suffix='.jsonl'
                ) as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                
                # Load candidates
                st.info(f"Loading candidates...")
                candidates = load_candidates_jsonl(tmp_path)
                
                # Limit to 100
                if len(candidates) > 100:
                    candidates = candidates[:100]
                    st.warning(f"Limited to first 100 candidates")
                
                st.success(f"Loaded {len(candidates)} candidates")
                
                # Filter honeypots
                st.info("Detecting honeypots...")
                detector = HoneypotDetector()
                valid_candidates, honeypots = detector.filter_honeypots(
                    [c['candidate_data'] for c in candidates]
                )
                
                if honeypots:
                    st.warning(f"Filtered {len(honeypots)} honeypots")
                
                # Update candidates list
                valid_ids = {c.get('candidate_id') for c in valid_candidates}
                candidates = [
                    c for c in candidates 
                    if c['candidate_id'] in valid_ids
                ]
                
                # Run pipeline
                st.info("Running screening pipeline...")
                
                temp_dir = tempfile.mkdtemp()
                save_temp_resumes(candidates, temp_dir)
                
                pipeline = BatchPipeline()
                result = pipeline.run(
                    resume_dir=temp_dir,
                    job_description=jd_text,
                    top_k=min(top_k, len(candidates))
                )
                
                st.success(
                    f"Processed {result['total_resumes_processed']} "
                    f"in {result['elapsed_seconds']:.1f}s"
                )
                
                # Apply behavioral signals
                st.info("Applying behavioral signals...")
                jd_requirements = parse_jd_requirements(jd_text)
                candidate_lookup = {
                    c['candidate_id']: c['candidate_data'] 
                    for c in candidates
                }
                
                for ranked_candidate in result['candidates']:
                    cid = ranked_candidate['resume_id']
                    full_data = candidate_lookup.get(cid, {})
                    redrob_signals = full_data.get('redrob_signals', {})
                    
                    behavioral_result = apply_behavioral_multiplier(
                        base_score=ranked_candidate['overall_score'],
                        redrob_signals=redrob_signals,
                        jd_requirements=jd_requirements
                    )
                    
                    ranked_candidate['overall_score'] = behavioral_result['final_score']
                
                # Re-rank
                result['candidates'].sort(
                    key=lambda x: x['overall_score'], 
                    reverse=True
                )
                for rank, c in enumerate(result['candidates'], 1):
                    c['rank'] = rank
                
                # Generate reasoning
                st.info("Generating reasoning...")
                reasoning_gen = ReasoningGenerator(jd_requirements)
                
                for ranked_candidate in result['candidates']:
                    cid = ranked_candidate['resume_id']
                    full_data = candidate_lookup.get(cid, {})
                    
                    reasoning = reasoning_gen.generate(
                        candidate=full_data,
                        rank=ranked_candidate['rank'],
                        scores=ranked_candidate['all_scores']
                    )
                    
                    ranked_candidate['reasoning'] = reasoning
                
                # Display results
                st.success("✅ Ranking complete!")
                
                # Show top candidates
                st.subheader("Top Candidates")
                
                for i, candidate in enumerate(result['candidates'][:10]):
                    with st.expander(
                        f"#{candidate['rank']} - {candidate['resume_id']} "
                        f"(Score: {candidate['overall_score']:.2f})"
                    ):
                        st.markdown(f"**Reasoning:** {candidate['reasoning']}")
                        
                        st.markdown("**Scores:**")
                        for dim, score in candidate['all_scores'].items():
                            st.progress(
                                score / 100, 
                                text=f"{dim}: {score:.1f}"
                            )
                
                # Download CSV
                csv_path = os.path.join(temp_dir, 'results.csv')
                write_submission_csv(result['candidates'], csv_path)
                
                with open(csv_path, 'r') as f:
                    csv_data = f.read()
                
                st.download_button(
                    "📥 Download CSV",
                    csv_data,
                    "ranking_results.csv",
                    "text/csv"
                )
                
                # Cleanup
                os.unlink(tmp_path)
                import shutil
                shutil.rmtree(temp_dir)
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
```

### Deploy to Streamlit Cloud:

1. **Push to GitHub** (the `app_streamlit.py` file)

2. **Go to:** https://streamlit.io/cloud

3. **Click "New app"**
   - Repository: Your GitHub repo
   - Branch: main
   - Main file: `app_streamlit.py`

4. **Click Deploy**

5. **Get public URL** (e.g., `https://your-app.streamlit.app`)

6. **Add URL to submission form**

---

## Option 2: Google Colab Notebook (Simplest - 1 hour)

### Create: `ATS_Demo.ipynb`

```python
# Cell 1: Setup
!git clone <your-repo-url>
%cd ats-intelligence
!pip install -r requirements.txt

# Cell 2: Upload files
from google.colab import files
uploaded = files.upload()  # Upload candidates.jsonl

# Cell 3: Create JD file
jd_text = """
Senior AI Engineer

Requirements:
- 5-9 years experience
- Python, embeddings, retrieval
- Location: Pune or Noida
"""

with open('jd.txt', 'w') as f:
    f.write(jd_text)

# Cell 4: Run screening
!python generate_submission.py \
  --candidates ./candidates.jsonl \
  --jd ./jd.txt \
  --output results.csv \
  --verbose

# Cell 5: Download results
files.download('results.csv')

# Cell 6: Show preview
import pandas as pd
df = pd.read_csv('results.csv')
df.head(10)
```

### Deploy:

1. Create notebook in Google Colab
2. Save to GitHub
3. Share public link
4. Add link to submission form

---

## Option 3: HuggingFace Spaces (Most Professional - 3 hours)

Similar to Streamlit but deployed on HuggingFace.

### Steps:

1. Create HF Space: https://huggingface.co/new-space
2. Choose "Streamlit" or "Gradio"
3. Upload `app_streamlit.py` (rename to `app.py`)
4. Upload `requirements.txt`
5. Push to HF Space repo
6. Get public URL

---

## What You Need to Provide Teammates

1. **This file** (`SANDBOX_BUILD_GUIDE.md`)
2. **GitHub repo access**
3. **Sample candidates.jsonl** (first 100 lines from hackathon data)
4. **Sample job_description.txt**

---

## Testing the Sandbox

Once deployed:

1. Upload sample `candidates.jsonl` (≤100 candidates)
2. Paste job description
3. Click "Run Ranking"
4. Verify:
   - ✅ Runs in <5 min
   - ✅ Produces CSV output
   - ✅ No errors
   - ✅ Shows top candidates with reasoning

---

## Troubleshooting

### Error: "Module not found"
**Solution:** Add missing package to `requirements.txt`

### Error: "Out of memory"
**Solution:** Limit candidates to 100 (already done in code)

### Error: "Timeout"
**Solution:** Use `--tiered` flag for faster processing

---

## Deliverable

**What to submit:**
- Public URL to working sandbox
- Example: `https://your-app.streamlit.app`

**Where to submit:**
- Add to submission form when uploading CSV
- Add to `submission_metadata.yaml`

---

## Questions?

Check these files in the repo:
- `IMPLEMENTATION_COMPLETE.md` - What we built
- `SUBMISSION_ALIGNMENT_CHECK.md` - Full requirements
- `generate_submission.py` - The code you're wrapping

**This is the last piece!** Once sandbox is deployed, submission is 100% complete. 🎉
