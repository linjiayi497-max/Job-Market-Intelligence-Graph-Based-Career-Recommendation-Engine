"""
Job Market Intelligence: Skill Analytics & Salary Prediction System
Main Entry Page (Streamlit)
"""
import streamlit as st
import os
import sys

# Add parent directory to path for importing processing modules
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

st.set_page_config(
    page_title="Job Market Analytics System",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🌟 Job Market Skill Analytics & Salary Prediction System")

st.markdown("""
---

This system analyzes **1.66 million** job postings from major recruitment platforms.
Using a deep learning NER model (MacBERT-BiLSTM-CRF) for skill extraction, combined with
XGBoost machine learning and SHAP interpretability analysis, it provides an end-to-end
intelligent analytics platform for job market insights.

### 🎯 Core Modules

| Module | Features | Navigation |
|--------|----------|------------|
| 📊 **Job Data Analysis** | Skill frequency, industry×skill heatmaps, city comparison, TF-IDF | 👈 Sidebar "Job Data Analysis" |
| 🎯 **Skill Gap Analysis** | Input personal skills → compare with target job → weighted coverage → gap ranking | 👈 Sidebar "Skill Gap Analysis" |
| 💸 **Salary Prediction** | Select skills/city/experience → real-time prediction → SHAP marginal value | 👈 Sidebar "Salary Prediction" |

---

### 📐 Technical Architecture

```
Raw Recruitment Data (57 CSV files, 1.7M records)
        │
        ▼
  MacBERT-BiLSTM-CRF NER Inference (GPU Server)
        │
        ▼
  Skill Extraction Results Parquet (1GB)
        │
        ▼
  Data Cleaning & Feature Engineering (Local)
        │
        ├──→ Module 1: Pandas Aggregation + TF-IDF Analysis
        ├──→ Module 2: Weighted Coverage Algorithm
        └──→ Module 3: XGBoost + SHAP Explainability
```

### 📊 Data Overview
""")

# Try loading data for overview metrics
try:
    from processing.data_loader import load_cleaned_data

    @st.cache_data(show_spinner=False)
    def _quick_stats():
        df = load_cleaned_data()
        return {
            "total": len(df),
            "industries": df["industry"].nunique() if "industry" in df.columns else df["行业"].nunique(),
            "avg_salary": df["monthly_salary"].mean() if "monthly_salary" in df.columns else df["月薪"].mean(),
            "avg_skills": df["skill_count"].mean() if "skill_count" in df.columns else df["技能数量"].mean(),
        }

    stats = _quick_stats()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("📋 Valid Job Records", f"{stats['total']:,}")
    with c2:
        st.metric("🏭 Industries Covered", f"{stats['industries']}")
    with c3:
        st.metric("💰 Avg. Monthly Salary", f"¥{stats['avg_salary']:,.0f}")
    with c4:
        st.metric("🧠 Avg. Skills/Job", f"{stats['avg_skills']:.1f}")

except Exception:
    st.warning("Data files not ready. Please run the data cleaning script first.")

st.markdown("---")
st.caption("© 2026 · Job Market Intelligence: Graph-Based Career Recommendation Engine · Streamlit Dashboard")
