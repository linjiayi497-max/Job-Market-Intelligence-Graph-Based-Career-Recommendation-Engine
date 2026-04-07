"""
Module 3: Salary Prediction Sandbox + Skill Marginal Value Analysis

Features:
  - Interactive salary prediction (select skills/city/experience → real-time prediction)
  - SHAP beeswarm plot & feature importance
  - Skill marginal value leaderboard
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import pickle
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

st.set_page_config(page_title="Salary Prediction", page_icon="💸", layout="wide")

# ─── Load Model ──────────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "models", "xgb_salary_model.pkl")

@st.cache_resource(show_spinner="Loading salary prediction model...")
def _load_model():
    if not os.path.exists(MODEL_PATH):
        return None
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)

model_data = _load_model()

st.title("💸 Salary Prediction Sandbox · Skill Value Analysis")

if model_data is None:
    st.error("⚠️ Model file not found. Please run `python scripts/train_xgb_model.py` first.")
    st.stop()

model = model_data["model"]
feature_names = model_data["feature_names"]
top_skills = model_data["top_skills"]
le_city = model_data["le_city"]
le_industry = model_data["le_industry"]
shap_values = model_data["shap_values"]
X_sample = model_data["X_sample"]
metrics = model_data["metrics"]
city_classes = model_data["city_classes"]
industry_classes = model_data["industry_classes"]

# ─── Model Performance Overview ──────────────────────────
st.markdown("### 📈 Model Performance")
mc1, mc2, mc3 = st.columns(3)
with mc1:
    st.metric("MAE (Mean Absolute Error)", f"¥{metrics['MAE']:,.0f}")
with mc2:
    st.metric("RMSE (Root Mean Sq. Error)", f"¥{metrics['RMSE']:,.0f}")
with mc3:
    st.metric("R² (Coefficient of Determination)", f"{metrics['R2']:.4f}")

st.divider()

# ─── Interactive Prediction ──────────────────────────────
st.markdown("### 🔮 Interactive Salary Prediction")
st.caption("Adjust the parameters below for real-time salary estimation")

col_left, col_right = st.columns([1, 2])

with col_left:
    exp_years = st.slider("Work Experience (years)", 0.0, 10.0, 3.0, 0.5, key="pred_exp")
    education = st.selectbox("Education", ["Any", "Associate", "Bachelor", "Master", "PhD"], index=2, key="pred_edu")
    edu_map = {"Any": 0, "Associate": 1, "Bachelor": 2, "Master": 3, "PhD": 4}
    edu_code = edu_map[education]

    city = st.selectbox("City", city_classes, index=0, key="pred_city")
    industry = st.selectbox("Industry", industry_classes, index=0, key="pred_ind")

    selected_skills = st.multiselect(
        "Select Skill Combination",
        top_skills, default=[], key="pred_skills",
        help="More skills = more accurate prediction",
    )

with col_right:
    # Build prediction vector
    city_code = list(city_classes).index(city) if city in city_classes else 0
    ind_code = list(industry_classes).index(industry) if industry in industry_classes else 0

    base = [exp_years, edu_code, city_code, ind_code, len(selected_skills)]
    skill_vec = [1.0 if s in selected_skills else 0.0 for s in top_skills]
    X_pred = np.array([base + skill_vec], dtype=np.float32)

    predicted_salary = model.predict(X_pred)[0]

    st.markdown("#### Prediction Result")

    pm1, pm2 = st.columns(2)
    with pm1:
        st.metric("Estimated Monthly Salary", f"¥{predicted_salary:,.0f}")
    with pm2:
        st.metric("Estimated Annual Salary (13 months)", f"¥{predicted_salary * 13:,.0f}")

    # Marginal value analysis
    st.markdown("#### 🧮 Skill Marginal Value (Real-time)")
    st.caption("Shows how much each additional skill would change the predicted salary")

    marginal_values = []
    for skill in top_skills[:30]:
        if skill not in selected_skills:
            test_skills = selected_skills + [skill]
            test_vec = [1.0 if s in test_skills else 0.0 for s in top_skills]
            X_test = np.array([base + test_vec], dtype=np.float32)
            pred_with = model.predict(X_test)[0]
            delta = pred_with - predicted_salary
            marginal_values.append({"Skill": skill, "Salary Increase": delta})

    if marginal_values:
        mv_df = pd.DataFrame(marginal_values).sort_values("Salary Increase", ascending=True)
        mv_df_show = mv_df.tail(15)

        fig_mv = px.bar(
            mv_df_show, x="Salary Increase", y="Skill",
            orientation="h", color="Salary Increase",
            color_continuous_scale="RdYlGn",
        )
        fig_mv.update_layout(height=450, showlegend=False, yaxis_title="")
        st.plotly_chart(fig_mv, use_container_width=True)

st.divider()

# ─── SHAP Global Analysis ──────────────────────────────
st.markdown("### 🐝 SHAP Feature Importance Analysis")
st.caption("Based on SHAP values from test set samples — reveals key salary drivers")

col_shap1, col_shap2 = st.columns(2)

with col_shap1:
    st.markdown("#### Feature Importance Ranking")
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    importance_df = pd.DataFrame({
        "Feature": feature_names,
        "Mean |SHAP|": mean_abs_shap,
    }).sort_values("Mean |SHAP|", ascending=True).tail(20)

    fig_imp = px.bar(
        importance_df, x="Mean |SHAP|", y="Feature",
        orientation="h", color="Mean |SHAP|",
        color_continuous_scale="Turbo",
    )
    fig_imp.update_layout(height=500, showlegend=False, yaxis_title="")
    st.plotly_chart(fig_imp, use_container_width=True)

with col_shap2:
    st.markdown("#### SHAP Beeswarm Plot")

    top_feat_idx = np.argsort(mean_abs_shap)[-15:][::-1]

    fig_bee = go.Figure()
    for rank, idx in enumerate(top_feat_idx):
        feat_name = feature_names[idx]
        sv = shap_values[:, idx]
        fv = X_sample[:, idx]

        fv_min, fv_max = fv.min(), fv.max()
        if fv_max > fv_min:
            fv_norm = (fv - fv_min) / (fv_max - fv_min)
        else:
            fv_norm = np.zeros_like(fv)

        jitter = np.random.RandomState(idx).uniform(-0.3, 0.3, len(sv))

        fig_bee.add_trace(go.Scatter(
            x=sv,
            y=[rank] * len(sv) + jitter,
            mode="markers",
            marker=dict(size=3, color=fv_norm, colorscale="RdBu_r", opacity=0.5),
            name=feat_name, showlegend=False,
            hovertemplate=f"{feat_name}<br>SHAP=%{{x:.0f}}<br>Feature=%{{text}}",
            text=[f"{v:.1f}" for v in fv],
        ))

    fig_bee.update_layout(
        yaxis=dict(
            tickvals=list(range(len(top_feat_idx))),
            ticktext=[feature_names[i] for i in top_feat_idx],
        ),
        xaxis_title="SHAP Value (impact on predicted salary, CNY/month)",
        height=550,
    )
    st.plotly_chart(fig_bee, use_container_width=True)

st.divider()

# ─── Data Export ──────────────────────────────────────────
with st.expander("📥 Export Analysis Data"):
    imp_full = pd.DataFrame({
        "Feature": feature_names,
        "Mean |SHAP|": mean_abs_shap,
    }).sort_values("Mean |SHAP|", ascending=False)

    st.download_button(
        "Download Feature Importance Ranking (CSV)",
        data=imp_full.to_csv(index=False, encoding="utf-8-sig"),
        file_name="shap_feature_importance.csv",
        mime="text/csv",
    )
