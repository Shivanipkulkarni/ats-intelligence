import streamlit as st
import requests

st.set_page_config(page_title="ATS Intelligence Engine", page_icon="🎯", layout="wide")

if "roles" not in st.session_state:
    st.session_state.roles = []
if "companies" not in st.session_state:
    st.session_state.companies = []
if "last_result" not in st.session_state:
    st.session_state.last_result = None

st.sidebar.header("Settings")
api_base = st.sidebar.text_input("API base URL", value="http://127.0.0.1:8000")
api_url = f"{api_base.rstrip('/')}/api/v1/candidate/score"

st.title("🎯 ATS Intelligence Engine")
st.caption("Hidden Talent Recovery System — Phase 1")

col1, col2 = st.columns(2)
with col1:
    resume_text = st.text_area(
        "Resume Text", height=280, placeholder="Paste the candidate's resume text here..."
    )
with col2:
    job_description = st.text_area(
        "Job Description", height=280, placeholder="Paste the job description here..."
    )

with st.expander("➕ Add structured work history (optional — improves career trajectory scoring)"):
    for i, role in enumerate(st.session_state.roles):
        c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 3, 0.4])
        role["title"] = c1.text_input("Title", value=role.get("title", ""), key=f"role_title_{i}")
        role["company"] = c2.text_input("Company", value=role.get("company", ""), key=f"role_company_{i}")
        role["duration_months"] = c3.number_input(
            "Months", min_value=0, value=role.get("duration_months", 12), key=f"role_dur_{i}"
        )
        resp_str = c4.text_input(
            "Responsibilities (comma-separated)",
            value=", ".join(role.get("responsibilities", [])),
            key=f"role_resp_{i}",
        )
        role["responsibilities"] = [r.strip() for r in resp_str.split(",") if r.strip()]
        if c5.button("✕", key=f"role_del_{i}"):
            st.session_state.roles.pop(i)
            st.rerun()
    if st.button("Add role"):
        st.session_state.roles.append(
            {"title": "", "company": "", "duration_months": 12, "responsibilities": []}
        )
        st.rerun()

with st.expander("➕ Add company context details (optional — improves company context scoring)"):
    for i, comp in enumerate(st.session_state.companies):
        c1, c2, c3, c4, c5, c6 = st.columns([2, 2, 1, 1.3, 2.2, 0.4])
        comp["company_name"] = c1.text_input(
            "Company Name", value=comp.get("company_name", ""), key=f"comp_name_{i}"
        )
        comp["role_title"] = c2.text_input(
            "Role Title", value=comp.get("role_title", ""), key=f"comp_role_{i}"
        )
        emp_str = c3.text_input(
            "Employees", value=str(comp.get("employee_count") or ""), key=f"comp_emp_{i}"
        )
        comp["employee_count"] = int(emp_str) if emp_str.strip().isdigit() else None
        fund_str = c4.text_input(
            "Funding Stage", value=comp.get("funding_stage") or "", key=f"comp_fund_{i}"
        )
        comp["funding_stage"] = fund_str or None
        resp_str = c5.text_input(
            "Responsibilities (comma-separated)",
            value=", ".join(comp.get("responsibilities", [])),
            key=f"comp_resp_{i}",
        )
        comp["responsibilities"] = [r.strip() for r in resp_str.split(",") if r.strip()]
        comp["duration_months"] = comp.get("duration_months", 12)
        if c6.button("✕", key=f"comp_del_{i}"):
            st.session_state.companies.pop(i)
            st.rerun()
    if st.button("Add company"):
        st.session_state.companies.append(
            {
                "company_name": "",
                "role_title": "",
                "employee_count": None,
                "funding_stage": None,
                "responsibilities": [],
                "duration_months": 12,
            }
        )
        st.rerun()

with st.expander("⚙️ Advanced: override module weights (optional)"):
    use_custom_weights = st.checkbox("Override default weights")
    w_semantic, w_career, w_company = 0.4, 0.3, 0.3
    if use_custom_weights:
        w_semantic = st.slider("Semantic Fit weight", 0.0, 1.0, w_semantic, 0.05)
        w_career = st.slider("Career Growth weight", 0.0, 1.0, w_career, 0.05)
        w_company = st.slider("Company Context weight", 0.0, 1.0, w_company, 0.05)
        st.caption(f"Sum: {w_semantic + w_career + w_company:.2f}")

st.divider()

if st.button("🔍 Score Candidate", type="primary", use_container_width=True):
    if not resume_text.strip() or not job_description.strip():
        st.error("Please provide both resume text and job description.")
    else:
        payload = {"resume_text": resume_text, "job_description": job_description}

        valid_roles = [r for r in st.session_state.roles if r.get("title") and r.get("company")]
        if valid_roles:
            payload["roles"] = valid_roles

        valid_companies = [
            c for c in st.session_state.companies if c.get("company_name") and c.get("role_title")
        ]
        if valid_companies:
            payload["companies"] = valid_companies

        if use_custom_weights:
            payload["weights"] = {
                "semantic_fit": w_semantic,
                "career_growth": w_career,
                "company_context": w_company,
            }

        resp = None
        with st.spinner("Scoring candidate..."):
            try:
                resp = requests.post(api_url, json=payload, timeout=30)
            except requests.exceptions.ConnectionError:
                st.error(f"Could not reach the API at {api_url}. Is the FastAPI server running?")
            except requests.exceptions.Timeout:
                st.error("The request timed out.")
            except Exception as e:
                st.error(f"Unexpected error: {e}")

        if resp is not None:
            if resp.status_code == 200:
                st.session_state.last_result = resp.json()
            elif resp.status_code == 422:
                st.error("Validation error:")
                for err in resp.json().get("detail", []):
                    loc = " → ".join(str(x) for x in err.get("loc", []))
                    st.write(f"- **{loc}**: {err.get('msg')}")
            else:
                st.error(f"Unexpected error ({resp.status_code}): {resp.text}")

data = st.session_state.last_result
if data:
    st.divider()
    st.subheader("Results")

    rc1, rc2 = st.columns(2)
    rc1.metric("Overall Score", f"{data['overall_hidden_talent_score']:.1f}")
    rc2.metric("Grade", data["grade"])

    verdict_lower = data["verdict"].lower()
    if any(w in verdict_lower for w in ["strong", "excellent", "high", "great", "good"]):
        st.success(f"**Verdict:** {data['verdict']}")
    elif any(w in verdict_lower for w in ["weak", "poor", "low", "reject"]):
        st.error(f"**Verdict:** {data['verdict']}")
    else:
        st.info(f"**Verdict:** {data['verdict']}")

    if data.get("flags"):
        st.warning("⚠️ " + " · ".join(data["flags"]))

    if data.get("top_reasons"):
        st.markdown("**Top Reasons**")
        for reason in data["top_reasons"]:
            st.write(f"- {reason}")

    st.divider()
    mc1, mc2, mc3 = st.columns(3)
    for name, mod, col in [
        ("Semantic Fit", data["semantic_fit"], mc1),
        ("Career Growth", data["career_growth"], mc2),
        ("Company Context", data["company_context"], mc3),
    ]:
        with col:
            st.markdown(f"**{name}**")
            score = mod["score"]
            bar_val = score / 100 if score > 1 else score
            st.progress(min(max(bar_val, 0.0), 1.0))
            st.caption(f"Score: {score} · Confidence: {mod['confidence']}")
            with st.expander("Reasons"):
                for r in mod["reasons"]:
                    st.write(f"- {r}")

    with st.expander("Weights used"):
        st.json(data.get("weights_used", {}))

    with st.expander("Raw JSON response"):
        st.json(data)