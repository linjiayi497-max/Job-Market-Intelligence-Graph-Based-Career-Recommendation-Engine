"""
Data Cleaning Pipeline

Reads the raw NER-extracted parquet file, performs salary parsing, experience
normalization, education encoding, and skill list generation.
Outputs a cleaned parquet file ready for analytics and model training.
"""
import pandas as pd
import numpy as np
import re
import os
import logging
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def parse_salary(salary_str: str) -> float:
    """
    Parse Chinese salary strings into average monthly salary (numeric, in CNY).
    Handles formats like: '8千-1.2万', '6千-8千·13薪', '1.4万-2.8万'

    Args:
        salary_str: Raw salary string from job posting

    Returns:
        Average monthly base salary in CNY, or NaN if unparseable
    """
    if pd.isna(salary_str) or not isinstance(salary_str, str):
        return np.nan

    # Remove suffixes like '·13薪', '/天', '/月'
    base_salary = salary_str.split('·')[0].split('/')[0].strip()

    def extract_value(s):
        """Extract numeric value with unit conversion (万=10000, 千=1000)."""
        s = s.strip()
        val = re.findall(r"[\d\.]+", s)
        if not val:
            return None
        num = float(val[0])
        if '万' in s:
            num *= 10000
        elif '千' in s:
            num *= 1000
        return num

    # Handle range format (e.g., '8千-1.2万')
    if '-' in base_salary:
        parts = base_salary.split('-')
        if len(parts) == 2:
            lower = extract_value(parts[0])
            upper = extract_value(parts[1])
            if lower is not None and upper is not None:
                return (lower + upper) / 2.0

    # Handle single value or 'X元以上' format
    val = extract_value(base_salary)
    return val


def parse_experience(exp_str: str) -> float:
    """
    Parse work experience requirement into numeric years.
    '经验不限'/'无经验' -> 0, '1-3年' -> 2.0 (midpoint)

    Args:
        exp_str: Raw experience requirement string

    Returns:
        Midpoint years of experience, or NaN if unparseable
    """
    if pd.isna(exp_str) or not isinstance(exp_str, str):
        return np.nan

    if '无经验' in exp_str or '经验不限' in exp_str or '应届生' in exp_str:
        return 0.0

    if '-' in exp_str:
        val = re.findall(r"[\d\.]+", exp_str)
        if len(val) >= 2:
            return (float(val[0]) + float(val[1])) / 2.0

    val = re.findall(r"[\d\.]+", exp_str)
    if val:
        return float(val[0])

    return np.nan


def parse_education(edu_str: str) -> int:
    """
    Encode education level as ordinal numeric value.

    Mapping: 博士(PhD)=4, 硕士(Master)=3, 本科(Bachelor)=2,
             大专(Associate)=1, Other/不限=0

    Args:
        edu_str: Raw education requirement string

    Returns:
        Integer encoding of education level
    """
    if pd.isna(edu_str) or not isinstance(edu_str, str):
        return 0

    if '博士' in edu_str:
        return 4
    elif '硕士' in edu_str:
        return 3
    elif '本科' in edu_str:
        return 2
    elif '大专' in edu_str:
        return 1
    else:
        return 0


def clean_data(input_parquet_path: str, output_parquet_path: str):
    """
    Main data cleaning pipeline.

    Steps:
    1. Remove records with no extracted skills
    2. Parse salary into numeric monthly values
    3. Parse experience into numeric years
    4. Encode education as ordinal integers
    5. Drop rows with unparseable salary or experience
    6. Generate skill list and skill count features
    7. Save cleaned dataset to parquet

    Args:
        input_parquet_path: Path to raw NER-extracted parquet file
        output_parquet_path: Path for output cleaned parquet file
    """
    logging.info(f"Loading raw data: {input_parquet_path}")
    df = pd.read_parquet(input_parquet_path)
    logging.info(f"Loaded successfully. Initial rows: {len(df)}")

    # Remove records with no extracted skills
    initial_len = len(df)
    df = df[df['Extracted_Skills'].notna()]
    df = df[df['Extracted_Skills'].str.strip() != ""]
    logging.info(f"After removing skill-less records: {len(df)} (removed {initial_len - len(df)})")

    # Parse salary field
    logging.info("Parsing salary field...")
    df['月薪'] = df['薪资'].apply(parse_salary)

    # Parse experience field
    logging.info("Parsing experience field...")
    df['经验年数'] = df['工作经验'].apply(parse_experience)

    # Encode education level
    logging.info("Encoding education level...")
    df['学历编码'] = df['学历'].apply(parse_education)

    # Drop rows with unparseable salary or experience
    df = df.dropna(subset=['月薪', '经验年数'])
    logging.info(f"After dropping unparseable records, final rows: {len(df)}")

    # Generate skill list and count features
    df['技能列表'] = df['Extracted_Skills'].apply(lambda x: [s.strip() for s in x.split(',') if s.strip()])
    df['技能数量'] = df['技能列表'].apply(len)

    # Remove rows with zero skills after parsing
    df = df[df['技能数量'] > 0]

    logging.info(f"Saving cleaned data to: {output_parquet_path}")
    df.to_parquet(output_parquet_path, index=False)
    logging.info("Data cleaning complete!")


if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    INPUT = os.path.join(BASE_DIR, "..", "ZhiLian_skills_extracted.parquet")
    OUTPUT = os.path.join(BASE_DIR, "processing", "ZhiLian_skills_cleaned.parquet")
    clean_data(INPUT, OUTPUT)
