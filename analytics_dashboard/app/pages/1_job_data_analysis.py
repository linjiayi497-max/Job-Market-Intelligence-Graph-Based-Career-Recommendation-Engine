"""
Module 1: Job Data & Skill Distribution Analysis

Features:
  - Top skill frequency bar chart
  - Industry × Skill heatmap
  - City skill distribution comparison
  - Salary band skill composition
  - TF-IDF skill weight analysis
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
import sys, os

# Add project root to sys.path for importing processing modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from processing.data_loader import (
    load_cleaned_data,
    extract_city_name,
    get_top_skills,
    build_skill_frequency_matrix,
    compute_skill_tfidf,
)

st.set_page_config(page_title="Job Data Analysis", page_icon="📊", layout="wide")

# ─── Data Loading (cached) ────────────────────────────────
@st.cache_data(show_spinner="Loading 1.66 million records...")
def _load():
    df = load_cleaned_data()
    df["城市"] = df["所在城市"].apply(extract_city_name)
    # Generate salary bands
    bins = [0, 5000, 8000, 12000, 20000, 50000, np.inf]
    labels = ["≤5k", "5k-8k", "8k-12k", "12k-20k", "20k-50k", "50k+"]
    df["薪资段"] = pd.cut(df["月薪"], bins=bins, labels=labels, right=False)
    return df

df = _load()

# ─── Page Title ──────────────────────────────────────────
st.title("📊 Job Data & Skill Distribution Analysis")
st.markdown(f"Dataset: **{len(df):,}** valid job postings across **{df['行业'].nunique()}** industries and **{df['城市'].nunique()}** cities.")
st.divider()

# ─── Sidebar Filters ──────────────────────────────────────
with st.sidebar:
    st.header("🔧 Filters")

    all_industries = sorted(df["行业"].dropna().unique())
    selected_industries = st.multiselect(
        "Select Industries (empty = all)",
        all_industries, default=[], key="ind_filter",
    )

    top_cities = df["城市"].value_counts().head(20).index.tolist()
    selected_cities = st.multiselect(
        "Select Cities (empty = all)",
        top_cities, default=[], key="city_filter",
    )

    top_n = st.slider("Show Top N Skills", 10, 50, 30)

# Apply filters
filtered = df.copy()
if selected_industries:
    filtered = filtered[filtered["行业"].isin(selected_industries)]
if selected_cities:
    filtered = filtered[filtered["城市"].isin(selected_cities)]

st.info(f"Filtered dataset size: **{len(filtered):,}** records")

# ─── Row 1: Overview Metrics ──────────────────────────────
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Avg. Monthly Salary", f"¥{filtered['月薪'].mean():,.0f}")
with col2:
    st.metric("Median Monthly Salary", f"¥{filtered['月薪'].median():,.0f}")
with col3:
    st.metric("Avg. Skills per Job", f"{filtered['技能数量'].mean():.1f}")
with col4:
    st.metric("Avg. Experience Req.", f"{filtered['经验年数'].mean():.1f} yrs")

st.divider()

# ─── Row 2: Top Skills + Salary Distribution ──────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🔥 Top N Skills")
    skill_counter = Counter()
    for sl in filtered["技能列表"]:
        if isinstance(sl, (list, np.ndarray)):
            skill_counter.update(sl)
    top_skills_data = skill_counter.most_common(top_n)
    if top_skills_data:
        skills_df = pd.DataFrame(top_skills_data, columns=["Skill", "Count"])
        fig_bar = px.bar(
            skills_df.iloc[::-1], x="Count", y="Skill",
            orientation="h", color="Count",
            color_continuous_scale="Viridis",
        )
        fig_bar.update_layout(height=600, showlegend=False, yaxis_title="")
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.warning("No skill data found")

with col_right:
    st.subheader("💰 Salary Distribution")
    salary_counts = filtered["薪资段"].value_counts().sort_index()
    fig_pie = px.pie(
        values=salary_counts.values,
        names=salary_counts.index.astype(str),
        color_discrete_sequence=px.colors.sequential.Tealgrn,
        hole=0.4,
    )
    fig_pie.update_layout(height=350)
    st.plotly_chart(fig_pie, use_container_width=True)

    st.subheader("📈 Education Distribution")
    edu_map = {0: "Any", 1: "Associate", 2: "Bachelor", 3: "Master", 4: "PhD"}
    edu_counts = filtered["学历编码"].map(edu_map).value_counts()
    fig_edu = px.bar(
        x=edu_counts.index, y=edu_counts.values,
        labels={"x": "Education", "y": "Count"},
        color=edu_counts.values, color_continuous_scale="Purples",
    )
    fig_edu.update_layout(height=250, showlegend=False)
    st.plotly_chart(fig_edu, use_container_width=True)

st.divider()

# ─── Row 3: Industry × Skill Heatmap ─────────────────────
st.subheader("🏭 Industry × Skill Frequency Heatmap")

@st.cache_data(show_spinner="Computing heatmap matrix...")
def _compute_heatmap(industries_list, _top_skills):
    sub = df[df["行业"].isin(industries_list)] if industries_list else df
    top_s = get_top_skills(sub, 20)
    matrix = build_skill_frequency_matrix(sub, "行业", top_s)
    top_ind = sub["行业"].value_counts().head(15).index.tolist()
    matrix = matrix.loc[matrix.index.isin(top_ind)]
    return matrix

heatmap_industries = selected_industries if selected_industries else []
matrix = _compute_heatmap(heatmap_industries, top_n)

if not matrix.empty:
    fig_heat = px.imshow(
        matrix.values, x=matrix.columns.tolist(), y=matrix.index.tolist(),
        color_continuous_scale="YlOrRd", aspect="auto",
        labels=dict(color="Frequency"),
    )
    fig_heat.update_layout(height=500)
    st.plotly_chart(fig_heat, use_container_width=True)
else:
    st.warning("No data for heatmap")

st.divider()

# ─── Row 4: City Skill Comparison ─────────────────────────
st.subheader("🌍 City × Skill Comparison")

compare_cities = st.multiselect(
    "Select 2-4 cities to compare",
    top_cities,
    default=top_cities[:3] if len(top_cities) >= 3 else top_cities,
    key="compare_cities",
)

if compare_cities:
    sub_city = filtered[filtered["城市"].isin(compare_cities)]
    city_skills = get_top_skills(sub_city, 15)
    city_matrix = build_skill_frequency_matrix(sub_city, "城市", city_skills)
    city_matrix = city_matrix.loc[city_matrix.index.isin(compare_cities)]

    if not city_matrix.empty:
        fig_city = px.imshow(
            city_matrix.values, x=city_matrix.columns.tolist(), y=city_matrix.index.tolist(),
            color_continuous_scale="Blues", aspect="auto",
        )
        fig_city.update_layout(height=350)
        st.plotly_chart(fig_city, use_container_width=True)

st.divider()

# ─── Row 5: Salary Band × Skill TF-IDF ───────────────────
st.subheader("📊 Salary Band × Skill TF-IDF Weights")

@st.cache_data(show_spinner="Computing TF-IDF...")
def _compute_tfidf():
    top_s = get_top_skills(df, 20)
    tfidf = compute_skill_tfidf(df, "薪资段", top_s)
    return tfidf

tfidf_matrix = _compute_tfidf()
if not tfidf_matrix.empty:
    fig_tfidf = px.imshow(
        tfidf_matrix.values, x=tfidf_matrix.columns.tolist(),
        y=tfidf_matrix.index.astype(str).tolist(),
        color_continuous_scale="Plasma", aspect="auto",
        labels=dict(color="TF-IDF"),
    )
    fig_tfidf.update_layout(height=400)
    st.plotly_chart(fig_tfidf, use_container_width=True)
    st.caption("💡 Higher TF-IDF indicates the skill is more 'signature' for that salary band.")

st.divider()

# ─── Data Export ──────────────────────────────────────────
with st.expander("📥 Export Analysis Data"):
    st.download_button(
        "Download Skill-Industry Frequency Matrix (CSV)",
        data=matrix.to_csv(encoding="utf-8-sig"),
        file_name="skill_industry_matrix.csv",
        mime="text/csv",
    )
