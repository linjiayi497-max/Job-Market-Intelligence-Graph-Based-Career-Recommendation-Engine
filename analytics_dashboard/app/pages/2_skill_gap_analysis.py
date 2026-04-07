"""
Module 2: Personal Skill Diagnosis & Job Gap Analysis

Features:
  - Manual skill selection or resume text parsing
  - Target job selection with search
  - Weighted skill coverage calculation
  - Gap priority report with radar chart
  - AI-powered learning path recommendations (via LLM)
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from collections import Counter
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from processing.data_loader import (
    load_cleaned_data,
    extract_city_name,
    get_top_skills,
    get_skills_by_job,
    compute_weighted_coverage,
)

# ─── LLM Configuration ─────────────────────────────────────
try:
    from openai import OpenAI
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

# NOTE: Set your API key via environment variable GROQ_API_KEY
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "openai/gpt-oss-120b"


def generate_learning_report(
    job_name: str, user_skills: list, matched_skills: list,
    gap_skills: list, gap_weights: list, coverage: float, avg_salary: float,
) -> str:
    """
    Generate a personalized skill gap analysis and learning path report via LLM.

    Args:
        job_name: Target job title
        user_skills: User's current skills
        matched_skills: Skills already matched
        gap_skills: Missing skills (sorted by importance)
        gap_weights: Importance weights for gap skills
        coverage: Current skill coverage ratio
        avg_salary: Average salary for the target job

    Returns:
        Markdown-formatted report string
    """
    gap_desc = "\n".join(
        [f"  - {s} (importance weight: {w*100:.1f}%)" for s, w in zip(gap_skills[:15], gap_weights[:15])]
    )
    matched_desc = ", ".join(matched_skills[:15]) if matched_skills else "None"

    prompt = f"""You are a senior career development and skills training consultant. Based on the following skill diagnostic data, generate a professional and practical personalized skill improvement and learning path report.

## Diagnostic Data

- **Target Position**: {job_name}
- **Market Average Monthly Salary**: ¥{avg_salary:,.0f}
- **Current Skill Coverage**: {coverage*100:.1f}%
- **Matched Skills**: {matched_desc}
- **Core Skill Gaps (by importance)**:
{gap_desc}

## Report Requirements

### 1. Overall Assessment
Brief evaluation of the candidate's current match with the target position (2-3 sentences).

### 2. Core Gap Analysis
For the top 5 gap skills, analyze:
- The role of this skill in the target position
- Why it is important
- Expected benefits after mastering it (with salary context)

### 3. Learning Path Recommendations
For each gap skill, recommend:
- Learning resources (online courses, books)
- Estimated learning timeline
- Practical suggestions (projects, certifications)

### 4. Action Plan
Provide a 3-6 month phased action plan.

### 5. Encouragement
A few positive and motivating sentences.

Please ensure the report is well-structured, practical, and professionally written.
"""

    client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=0.7,
        max_tokens=3000,
        messages=[
            {"role": "system", "content": "You are a senior career development consultant specializing in data-driven learning path recommendations."},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content.strip()


st.set_page_config(page_title="Skill Gap Analysis", page_icon="🎯", layout="wide")

# ─── Data Loading ──────────────────────────────────────────
@st.cache_data(show_spinner="Loading data...")
def _load():
    df = load_cleaned_data()
    df["城市"] = df["所在城市"].apply(extract_city_name)
    return df

@st.cache_data(show_spinner="Building skill pool...")
def _build_skill_pool(_df):
    """Build global skill pool and popular job list."""
    all_skills = get_top_skills(_df, 200)
    job_counts = _df["职位名称"].value_counts().head(100)
    return all_skills, job_counts.index.tolist()

df = _load()
all_skills, popular_jobs = _build_skill_pool(df)

# ─── Page Title ──────────────────────────────────────────
st.title("🎯 Personal Skill Diagnosis & Gap Analysis")
st.markdown("Compare your skills with target job requirements. Quantify gaps and get prioritized learning recommendations.")
st.divider()

# ─── Two-Column Layout ──────────────────────────────────
col_input, col_result = st.columns([1, 2])

with col_input:
    st.subheader("① Enter Your Skills")

    input_method = st.radio(
        "Skill input method",
        ["Manual Selection / Input", "Paste Text (Simple Matching)"],
        key="input_method",
    )

    user_skills = []

    if input_method == "Manual Selection / Input":
        user_skills = st.multiselect(
            "Select or search your skills",
            options=all_skills, default=[], key="manual_skills",
            help="Type to search keywords",
        )
        extra = st.text_input("Additional skills (comma-separated)", key="extra_skills")
        if extra:
            extras = [s.strip() for s in extra.replace("，", ",").replace(" ", ",").split(",") if s.strip()]
            user_skills = list(set(user_skills + extras))
    else:
        resume_text = st.text_area(
            "Paste your resume or skill description",
            height=200,
            placeholder="e.g., Proficient in Python, PyTorch, with ML project experience...",
        )
        if resume_text:
            matched = [s for s in all_skills if s.lower() in resume_text.lower()]
            user_skills = matched
            if matched:
                st.success(f"Identified {len(matched)} skills from text")
            else:
                st.warning("No matching skills found. Try manual selection.")

    if user_skills:
        st.markdown(f"**{len(user_skills)} skills entered:**")
        skill_tags = " ".join([f"`{s}`" for s in user_skills])
        st.markdown(skill_tags)

    st.divider()

    st.subheader("② Select Target Job")

    job_keyword = st.text_input(
        "Enter target job keyword",
        placeholder="e.g., Algorithm Engineer, Data Analyst...",
        key="job_keyword",
    )

    if job_keyword:
        matching_jobs = df[df["职位名称"].str.contains(job_keyword, case=False, na=False)]["职位名称"].value_counts().head(20)
        if not matching_jobs.empty:
            selected_job = st.selectbox(
                "Select specific job", matching_jobs.index.tolist(), key="selected_job",
            )
            st.caption(f"This job has {matching_jobs[selected_job]} postings in the dataset")
        else:
            selected_job = None
            st.warning(f"No jobs found matching '{job_keyword}'")
    else:
        selected_job = None

with col_result:
    st.subheader("③ Diagnosis Results")

    if not user_skills:
        st.info("👈 Please enter your skills first")
    elif not selected_job:
        st.info("👈 Please select a target job")
    else:
        # Get target job skill requirements and weights
        job_mask = df["职位名称"] == selected_job
        job_df = df[job_mask]

        skill_counter = Counter()
        for sl in job_df["技能列表"]:
            if isinstance(sl, (list, np.ndarray)):
                skill_counter.update(sl)

        if not skill_counter:
            st.error("Insufficient skill data for this job")
        else:
            # Normalize weights
            total_mentions = sum(skill_counter.values())
            job_skills_weighted = {s: c / total_mentions for s, c in skill_counter.most_common(50)}

            # Compute weighted coverage
            result = compute_weighted_coverage(user_skills, job_skills_weighted)

            # ─── Overview Metrics ───
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Weighted Skill Coverage", f"{result['coverage'] * 100:.1f}%")
            with m2:
                st.metric("Matched Skills", f"{len(result['matched'])} items")
            with m3:
                st.metric("Skill Gaps", f"{len(result['gap'])} items")

            st.divider()

            # ─── Radar Chart ───
            st.markdown("#### 🕸️ Skill Coverage Radar Chart")

            radar_skills = list(job_skills_weighted.keys())[:12]
            radar_job_vals = [job_skills_weighted[s] for s in radar_skills]
            max_val = max(radar_job_vals) if radar_job_vals else 1
            radar_job_norm = [v / max_val for v in radar_job_vals]
            radar_user_norm = [1.0 if s in set(user_skills) else 0.0 for s in radar_skills]

            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=radar_job_norm + [radar_job_norm[0]],
                theta=radar_skills + [radar_skills[0]],
                fill="toself", name="Job Requirements",
                fillcolor="rgba(99, 110, 250, 0.2)",
                line=dict(color="rgba(99, 110, 250, 0.8)"),
            ))
            fig_radar.add_trace(go.Scatterpolar(
                r=radar_user_norm + [radar_user_norm[0]],
                theta=radar_skills + [radar_skills[0]],
                fill="toself", name="Your Skills",
                fillcolor="rgba(0, 204, 150, 0.2)",
                line=dict(color="rgba(0, 204, 150, 0.8)"),
            ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 1.1])),
                height=450, showlegend=True,
            )
            st.plotly_chart(fig_radar, use_container_width=True)

            # ─── Gap Skills Priority List ───
            st.markdown("#### 🚨 Skill Gap Priority List")
            st.caption("Sorted by importance weight in the target job (descending)")

            if result["gap"]:
                gap_df = pd.DataFrame({
                    "Gap Skill": result["gap"][:20],
                    "Importance": [f"{w*100:.2f}%" for w in result["gap_weights"][:20]],
                    "Weight": result["gap_weights"][:20],
                })

                fig_gap = px.bar(
                    gap_df.iloc[::-1], x="Weight", y="Gap Skill",
                    orientation="h", color="Weight",
                    color_continuous_scale="Reds",
                )
                fig_gap.update_layout(height=500, showlegend=False, yaxis_title="")
                st.plotly_chart(fig_gap, use_container_width=True)
            else:
                st.success("🎉 Congratulations! You fully cover all core skill requirements!")

            # ─── AI Learning Path Report ───
            st.divider()
            st.markdown("#### 🤖 AI-Powered Learning Path Report")

            if not LLM_AVAILABLE:
                st.warning("⚠️ Please install openai library: `pip install openai`")
            elif not GROQ_API_KEY:
                st.warning("⚠️ Please set the GROQ_API_KEY environment variable.")
            elif not result["gap"]:
                st.success("You've fully covered the target skills — no gap report needed!")
            else:
                st.caption("AI generates a personalized learning path based on your skill gap data")

                if st.button("🚀 Generate AI Learning Path Report", type="primary", use_container_width=True):
                    avg_salary = job_df["月薪"].mean()

                    with st.spinner("🤖 AI is analyzing your skill data... (15-30 seconds)"):
                        try:
                            report = generate_learning_report(
                                job_name=selected_job,
                                user_skills=user_skills,
                                matched_skills=result["matched"],
                                gap_skills=result["gap"][:15],
                                gap_weights=result["gap_weights"][:15],
                                coverage=result["coverage"],
                                avg_salary=avg_salary,
                            )
                            st.session_state["llm_report"] = report
                            st.session_state["llm_report_job"] = selected_job
                        except Exception as e:
                            st.error(f"❌ AI report generation failed: {str(e)}")

                # Display generated report
                if "llm_report" in st.session_state and st.session_state.get("llm_report_job") == selected_job:
                    st.markdown("---")
                    st.markdown(st.session_state["llm_report"])
                    st.download_button(
                        "📥 Download Report (Markdown)",
                        data=st.session_state["llm_report"],
                        file_name=f"skill_gap_report_{selected_job}.md",
                        mime="text/markdown",
                    )

            st.divider()

            # ─── Matched Skills Detail ───
            with st.expander("✅ Matched Skills Detail"):
                if result["matched"]:
                    st.markdown(" ".join([f"✅ `{s}`" for s in result["matched"]]))
                else:
                    st.info("No matched skills yet")

            # ─── Job Salary Reference ───
            with st.expander("💰 Job Salary Reference"):
                avg_salary = job_df["月薪"].mean()
                median_salary = job_df["月薪"].median()
                mc1, mc2 = st.columns(2)
                with mc1:
                    st.metric("Avg. Monthly Salary", f"¥{avg_salary:,.0f}")
                with mc2:
                    st.metric("Median Monthly Salary", f"¥{median_salary:,.0f}")

                fig_sal = px.histogram(
                    job_df, x="月薪", nbins=30,
                    labels={"月薪": "Monthly Salary (CNY)"},
                    color_discrete_sequence=["#636EFA"],
                )
                fig_sal.update_layout(height=250)
                st.plotly_chart(fig_sal, use_container_width=True)
