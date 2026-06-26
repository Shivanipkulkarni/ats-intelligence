"""
ATS Intelligence Engine - Sandbox Demo
Hackathon submission sandbox: accepts ≤100 candidates, ranks them, outputs CSV.
"""

import streamlit as st
import json
import tempfile
import os
import shutil
import sys
import io

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(
    page_title="ATS Intelligence Engine",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 ATS Intelligence Engine")
st.markdown("**Hackathon Sandbox** · Intelligent resume ranking across 10 scoring dimensions")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("How it works")
    st.markdown("""
    1. Upload a `.jsonl` file (≤ 100 candidates)
    2. Paste the job description
    3. Choose how many top candidates to rank
    4. Click **Run Ranking**
    5. Download the ranked CSV

    **Scoring dimensions:**
    - Semantic fit (TF-IDF + LSA)
    - Career trajectory & growth
    - Company context
    - Skill currency / decay
    - Resilience signals
    - Narrative coherence
    - Team portfolio
    - Artifact complexity
    - Counterfactual readiness
    - Behavioral signals (multiplier)

    **Honeypot detection** is applied automatically.
    """)
    st.info("Runs on CPU · completes in < 5 min for 100 candidates")

# ── Inputs ───────────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 1])

with col1:
    uploaded_file = st.file_uploader(
        "Upload candidates.jsonl  (max 100 candidates)",
        type=["jsonl"],
        help="Each line must be a JSON object with candidate_id and profile fields.",
    )

with col2:
    jd_text = st.text_area(
        "Job Description",
        height=220,
        placeholder="Paste the full job description here…",
    )

top_k = st.slider("Number of top candidates to include in output", 10, 100, 50)

run_btn = st.button("🚀 Run Ranking", type="primary", use_container_width=True)

# ── Pipeline ─────────────────────────────────────────────────────────────────
if run_btn:
    if not uploaded_file:
        st.error("Please upload a candidates.jsonl file.")
        st.stop()
    if not jd_text.strip():
        st.error("Please enter a job description.")
        st.stop()

    progress = st.progress(0, text="Starting…")
    status   = st.empty()

    try:
        # ── lazy imports (keeps startup fast) ────────────────────────────────
        from generate_submission import load_candidates_jsonl, save_temp_resumes
        from app.services.batch.pipeline import BatchPipeline
        from app.services.reasoning_generator import ReasoningGenerator, parse_jd_requirements
        from app.services.behavioral_signals.scorer import apply_behavioral_multiplier
        from app.services.honeypot_detector import HoneypotDetector

        # Step 1 – save upload to disk
        status.info("📂 Loading candidates…")
        progress.progress(5, text="Loading candidates…")

        tmp_jsonl = tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl")
        tmp_jsonl.write(uploaded_file.getvalue())
        tmp_jsonl.close()

        candidates = load_candidates_jsonl(tmp_jsonl.name)
        os.unlink(tmp_jsonl.name)

        if len(candidates) == 0:
            st.error("No valid candidates found in the uploaded file.")
            st.stop()

        if len(candidates) > 100:
            candidates = candidates[:100]
            st.warning("File contained > 100 candidates — truncated to first 100.")

        st.success(f"✅ Loaded **{len(candidates)}** candidates")
        progress.progress(15, text="Detecting honeypots…")

        # Step 2 – honeypot detection
        status.info("🍯 Detecting honeypot candidates…")
        detector = HoneypotDetector(strict_mode=False)
        valid_data, honeypots = detector.filter_honeypots(
            [c["candidate_data"] for c in candidates]
        )

        if honeypots:
            st.warning(f"Filtered out **{len(honeypots)}** honeypot candidate(s).")

        valid_ids = {c.get("candidate_id") for c in valid_data}
        candidates = [c for c in candidates if c["candidate_id"] in valid_ids]
        st.success(f"✅ **{len(candidates)}** valid candidates after honeypot filter")
        progress.progress(30, text="Running screening pipeline…")

        # Step 3 – pipeline
        status.info("⚙️ Running screening pipeline (this is the slow part)…")
        temp_dir = tempfile.mkdtemp()
        save_temp_resumes(candidates, temp_dir)

        pipeline = BatchPipeline()
        result = pipeline.run_tiered(
            resume_dir=temp_dir,
            job_description=jd_text,
            top_k=min(top_k, len(candidates)),
        )

        st.success(
            f"✅ Screened **{result['total_resumes_processed']}** resumes "
            f"in **{result['elapsed_seconds']:.1f}s**"
        )
        progress.progress(60, text="Applying behavioral signals…")

        # Step 4 – behavioral multiplier
        status.info("📊 Applying behavioral signals…")
        jd_requirements  = parse_jd_requirements(jd_text)
        candidate_lookup = {c["candidate_id"]: c["candidate_data"] for c in candidates}

        for rc in result["candidates"]:
            cid            = rc["resume_id"]
            full_data      = candidate_lookup.get(cid, {})
            redrob_signals = full_data.get("redrob_signals", {})

            beh = apply_behavioral_multiplier(
                base_score=rc["overall_score"],
                redrob_signals=redrob_signals,
                jd_requirements=jd_requirements,
            )
            rc["base_score"]             = rc["overall_score"]
            rc["overall_score"]          = beh["final_score"]
            rc["behavioral_multiplier"]  = beh["behavioral_multiplier"]

        result["candidates"].sort(key=lambda x: x["overall_score"], reverse=True)
        for new_rank, rc in enumerate(result["candidates"], 1):
            rc["rank"] = new_rank

        progress.progress(75, text="Generating reasoning…")

        # Step 5 – reasoning
        status.info("💬 Generating candidate reasoning…")
        reasoning_gen = ReasoningGenerator(jd_requirements)

        for rc in result["candidates"]:
            cid       = rc["resume_id"]
            full_data = candidate_lookup.get(cid, {})
            rc["reasoning"] = reasoning_gen.generate(
                candidate=full_data,
                rank=rc["rank"],
                scores=rc["all_scores"],
            )
            rc["candidate_data"] = full_data

        progress.progress(90, text="Building CSV…")

        # Step 6 – build CSV in-memory (no 100-row requirement for sandbox)
        status.info("📄 Building output CSV…")

        csv_lines = ["candidate_id,rank,score,reasoning"]
        for rc in result["candidates"]:
            cid       = rc.get("resume_id") or rc.get("candidate_id", "")
            rank      = rc.get("rank", "")
            score     = rc.get("overall_score", 0) / 100
            reasoning = rc.get("reasoning", "").replace('"', "'").replace("\n", " ").replace("\r", "")
            csv_lines.append(f'{cid},{rank},{score:.4f},"{reasoning}"')

        csv_data = "\n".join(csv_lines)

        shutil.rmtree(temp_dir, ignore_errors=True)

        progress.progress(100, text="Done!")
        status.success("🎉 Ranking complete!")

        # ── Results display ───────────────────────────────────────────────────
        st.markdown("---")
        st.subheader("🏆 Top Candidates")

        top_display = result["candidates"][:10]
        for rc in top_display:
            label = (
                f"#{rc['rank']}  ·  {rc['resume_id']}  "
                f"·  Score: {rc['overall_score']:.1f}"
            )
            with st.expander(label):
                st.markdown(f"**Reasoning:** {rc.get('reasoning', '—')}")
                st.markdown("**Dimension scores:**")
                scores = rc.get("all_scores", {})
                if scores:
                    cols = st.columns(3)
                    for i, (dim, val) in enumerate(scores.items()):
                        cols[i % 3].metric(dim.replace("_", " ").title(), f"{val:.1f}")
                else:
                    st.write("(No dimension breakdown available)")

        # ── Download ──────────────────────────────────────────────────────────
        st.markdown("---")
        st.download_button(
            label="📥 Download Ranked CSV",
            data=csv_data,
            file_name="ranking_results.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary",
        )

        st.info(
            f"**{len(result['candidates'])} candidates** ranked  ·  "
            f"processed in **{result['elapsed_seconds']:.1f}s**"
        )

    except Exception as exc:
        import traceback
        st.error(f"❌ Error: {exc}")
        st.code(traceback.format_exc())
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass
