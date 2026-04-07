"""
Shared Data Loader Module

All Streamlit pages use this module to load and cache the cleaned dataset.
Provides utility functions for skill frequency analysis, TF-IDF computation,
and weighted skill coverage calculation.
"""
import os
import re
import pandas as pd
import numpy as np
from collections import Counter

# Data file path (relative to this processing directory)
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLEANED_DATA_PATH = os.path.join(_BASE_DIR, "ZhiLian_skills_cleaned.parquet")


def load_cleaned_data() -> pd.DataFrame:
    """Load the cleaned parquet dataset."""
    if not os.path.exists(CLEANED_DATA_PATH):
        raise FileNotFoundError(f"Cleaned data file not found: {CLEANED_DATA_PATH}")
    return pd.read_parquet(CLEANED_DATA_PATH)


def extract_city_name(city_raw: str) -> str:
    """
    Extract the primary city name from a hierarchical location string.
    Example: '成都·武侯·桂溪' -> '成都'
    """
    if pd.isna(city_raw) or not isinstance(city_raw, str):
        return "Unknown"
    parts = city_raw.split("·")
    return parts[0].strip() if parts else "Unknown"


def get_top_skills(df: pd.DataFrame, top_n: int = 50) -> list:
    """
    Count and return the top N most frequent skills across the dataset.

    Args:
        df: DataFrame with a '技能列表' (skill_list) column
        top_n: Number of top skills to return

    Returns:
        List of skill names ordered by frequency
    """
    skill_counter = Counter()
    for skill_list in df["技能列表"]:
        if isinstance(skill_list, (list, np.ndarray)):
            skill_counter.update(skill_list)
    return [s for s, _ in skill_counter.most_common(top_n)]


def get_skills_by_job(df: pd.DataFrame, job_keyword: str, top_n: int = 30) -> list:
    """
    Get the top skills for a specific job title keyword.

    Args:
        df: Full dataset DataFrame
        job_keyword: Keyword to filter job titles
        top_n: Number of top skills to return

    Returns:
        List of skill names for the filtered job
    """
    mask = df["职位名称"].str.contains(job_keyword, case=False, na=False)
    sub = df.loc[mask]
    if sub.empty:
        return []
    skill_counter = Counter()
    for skill_list in sub["技能列表"]:
        if isinstance(skill_list, (list, np.ndarray)):
            skill_counter.update(skill_list)
    return [s for s, _ in skill_counter.most_common(top_n)]


def build_skill_frequency_matrix(df: pd.DataFrame, group_col: str, top_skills: list) -> pd.DataFrame:
    """
    Build a skill × group frequency matrix.

    Args:
        df: Dataset DataFrame
        group_col: Column to group by (e.g., 'industry', 'city', 'salary_band')
        top_skills: List of skills to include

    Returns:
        DataFrame with groups as rows and skills as columns (frequency values)
    """
    records = []
    for group_val, sub_df in df.groupby(group_col):
        skill_counter = Counter()
        for skill_list in sub_df["技能列表"]:
            if isinstance(skill_list, (list, np.ndarray)):
                skill_counter.update(skill_list)
        total = sum(skill_counter.values()) if skill_counter else 1
        row = {"group": group_val}
        for skill in top_skills:
            row[skill] = skill_counter.get(skill, 0) / total
        records.append(row)

    result = pd.DataFrame(records).set_index("group")
    return result


def compute_skill_tfidf(df: pd.DataFrame, group_col: str, top_skills: list) -> pd.DataFrame:
    """
    Compute TF-IDF values for skills across groups.

    TF = skill occurrences in group / total skill mentions in group
    IDF = log(total groups / groups containing the skill)

    Args:
        df: Dataset DataFrame
        group_col: Column to group by
        top_skills: List of skills to analyze

    Returns:
        DataFrame with TF-IDF values (groups × skills)
    """
    groups = df[group_col].unique()
    n_groups = len(groups)

    # Count skill occurrences per group
    group_skill_counts = {}
    for g, sub_df in df.groupby(group_col):
        counter = Counter()
        for sl in sub_df["技能列表"]:
            if isinstance(sl, (list, np.ndarray)):
                counter.update(sl)
        group_skill_counts[g] = counter

    # Compute IDF (document frequency)
    doc_freq = {}
    for skill in top_skills:
        doc_freq[skill] = sum(1 for g in groups if group_skill_counts.get(g, {}).get(skill, 0) > 0)

    # Compute TF-IDF for each group × skill
    records = []
    for g in groups:
        counter = group_skill_counts.get(g, Counter())
        total = sum(counter.values()) if counter else 1
        row = {"group": g}
        for skill in top_skills:
            tf = counter.get(skill, 0) / total
            idf = np.log(n_groups / (1 + doc_freq.get(skill, 0)))
            row[skill] = tf * idf
        records.append(row)

    return pd.DataFrame(records).set_index("group")


def compute_weighted_coverage(user_skills: list, job_skills_weighted: dict) -> dict:
    """
    Compute weighted skill coverage between user skills and job requirements.

    Args:
        user_skills: List of skills the user possesses
        job_skills_weighted: Dict of {skill_name: weight} for the target job

    Returns:
        Dict with keys:
            - 'coverage': Weighted coverage ratio (float)
            - 'matched': List of matched skills
            - 'gap': List of missing skills (sorted by weight desc)
            - 'gap_weights': Corresponding weights for gap skills
    """
    user_set = set(user_skills)
    total_weight = sum(job_skills_weighted.values())
    if total_weight == 0:
        return {"coverage": 0.0, "matched": [], "gap": [], "gap_weights": []}

    matched_weight = sum(w for s, w in job_skills_weighted.items() if s in user_set)
    coverage = matched_weight / total_weight

    matched = [s for s in job_skills_weighted if s in user_set]
    gap_items = [(s, w) for s, w in job_skills_weighted.items() if s not in user_set]
    gap_items.sort(key=lambda x: x[1], reverse=True)

    return {
        "coverage": coverage,
        "matched": matched,
        "gap": [s for s, _ in gap_items],
        "gap_weights": [w for _, w in gap_items],
    }
