"""
XGBoost Salary Prediction Model Training Script

Trains an XGBoost regressor to predict monthly salary based on:
- Work experience (years)
- Education level (ordinal encoded)
- City (label encoded)
- Industry (label encoded)
- Skill dummy variables (top 100 skills as binary features)

Also computes SHAP values for model interpretability and saves
the complete model package for the Streamlit dashboard.
"""
import os
import pickle
import pandas as pd
import numpy as np
from collections import Counter
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import xgboost as xgb
import shap
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ─── Paths ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "..", "processing", "ZhiLian_skills_cleaned.parquet")
MODEL_DIR = os.path.join(BASE_DIR, "..", "models")
os.makedirs(MODEL_DIR, exist_ok=True)


def extract_city(raw: str) -> str:
    """Extract primary city name from hierarchical location string."""
    if pd.isna(raw) or not isinstance(raw, str):
        return "Unknown"
    return raw.split("·")[0].strip()


def build_features(df: pd.DataFrame, top_skills: list):
    """
    Build the feature matrix for model training.

    Features include:
    - experience_years (continuous)
    - education_code (ordinal: 0-4)
    - city_code (label encoded)
    - industry_code (label encoded)
    - skill_count (number of skills)
    - skill_dummy_1 ... skill_dummy_N (binary: 0/1 for each top skill)

    Returns:
        X: Feature matrix (numpy array)
        feature_names: List of feature names
        le_city: Fitted LabelEncoder for cities
        le_industry: Fitted LabelEncoder for industries
    """
    df = df.copy()
    df["city"] = df["所在城市"].apply(extract_city)

    # Encode categorical features
    le_city = LabelEncoder()
    le_industry = LabelEncoder()
    df["city_code"] = le_city.fit_transform(df["city"].fillna("Unknown"))
    df["industry_code"] = le_industry.fit_transform(df["行业"].fillna("Unknown"))

    # Base numeric features
    base_features = df[["经验年数", "学历编码", "city_code", "industry_code", "技能数量"]].values

    # Skill dummy variables
    skill_to_idx = {s: i for i, s in enumerate(top_skills)}
    n_skills = len(top_skills)
    rows = []
    for skill_list in df["技能列表"]:
        row = np.zeros(n_skills, dtype=np.float32)
        if isinstance(skill_list, (list, np.ndarray)):
            for s in skill_list:
                if s in skill_to_idx:
                    row[skill_to_idx[s]] = 1.0
        rows.append(row)

    skill_matrix = np.array(rows)

    # Concatenate all features
    X = np.hstack([base_features, skill_matrix])
    feature_names = ["experience_years", "education_code", "city_code",
                     "industry_code", "skill_count"] + top_skills

    return X, feature_names, le_city, le_industry


def main():
    logging.info("Loading data...")
    df = pd.read_parquet(DATA_PATH)
    logging.info(f"Dataset size: {len(df)}")

    # Remove salary outliers (bottom 1% and top 1%)
    q_low = df["月薪"].quantile(0.01)
    q_high = df["月薪"].quantile(0.99)
    df = df[(df["月薪"] >= q_low) & (df["月薪"] <= q_high)]
    logging.info(f"After outlier removal: {len(df)}")

    # Determine top skills for feature engineering
    skill_counter = Counter()
    for sl in df["技能列表"]:
        if isinstance(sl, (list, np.ndarray)):
            skill_counter.update(sl)
    top_skills = [s for s, _ in skill_counter.most_common(100)]
    logging.info(f"Selected top {len(top_skills)} skills as features")

    # Build feature matrix
    logging.info("Building feature matrix...")
    X, feature_names, le_city, le_industry = build_features(df, top_skills)
    y = df["月薪"].values
    logging.info(f"Feature matrix shape: {X.shape}")

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    logging.info(f"Train set: {X_train.shape[0]}, Test set: {X_test.shape[0]}")

    # Train XGBoost
    logging.info("Training XGBoost...")
    model = xgb.XGBRegressor(
        n_estimators=300, max_depth=8, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8,
        reg_alpha=0.1, reg_lambda=1.0,
        random_state=42, n_jobs=-1, tree_method="hist",
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=50)

    # Evaluate
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    logging.info(f"Test MAE: {mae:.0f}")
    logging.info(f"Test RMSE: {rmse:.0f}")
    logging.info(f"Test R²: {r2:.4f}")

    # SHAP analysis (on sampled subset for memory efficiency)
    logging.info("Computing SHAP values (sampling 5000 records)...")
    sample_idx = np.random.RandomState(42).choice(len(X_test), min(5000, len(X_test)), replace=False)
    X_sample = X_test[sample_idx]
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)

    # Save model and metadata
    logging.info("Saving model and metadata...")
    model_data = {
        "model": model,
        "feature_names": feature_names,
        "top_skills": top_skills,
        "le_city": le_city,
        "le_industry": le_industry,
        "shap_values": shap_values,
        "X_sample": X_sample,
        "metrics": {"MAE": mae, "RMSE": rmse, "R2": r2},
        "city_classes": le_city.classes_.tolist(),
        "industry_classes": le_industry.classes_.tolist(),
    }

    model_path = os.path.join(MODEL_DIR, "xgb_salary_model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(model_data, f)

    logging.info(f"Model saved to: {model_path}")
    logging.info("All done!")


if __name__ == "__main__":
    main()
