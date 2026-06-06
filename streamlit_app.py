from __future__ import annotations

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import streamlit as st

from career_service import analyze_career, available_jobs, available_skills


BRAND_BLUE = "#17324d"
BRAND_ORANGE = "#f28c28"


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{ background: #f7f9fb; }}
        .product-header {{
          background: {BRAND_BLUE};
          color: white;
          padding: 18px 20px;
          border-radius: 6px;
          margin-bottom: 18px;
        }}
        .product-header h1 {{
          margin: 0;
          font-size: 26px;
          letter-spacing: 0;
        }}
        .product-header p {{
          margin: 5px 0 0 0;
          color: #d7e1ec;
        }}
        .mode-badge {{
          display: inline-block;
          background: #fff3e0;
          color: #8a4d00;
          border: 1px solid #ffd49a;
          border-radius: 4px;
          padding: 4px 8px;
          font-size: 13px;
          margin-bottom: 12px;
        }}
        .course-card, .job-card {{
          background: white;
          border: 1px solid #e3e8ef;
          border-radius: 6px;
          padding: 12px 14px;
          margin-bottom: 10px;
          box-shadow: 0 2px 10px rgba(23, 50, 77, .05);
        }}
        .course-card strong, .job-card strong {{ color: {BRAND_BLUE}; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def read_neo4j_config() -> dict[str, str]:
    try:
        neo4j_cfg = st.secrets.get("neo4j", {})
        return {
            "uri": neo4j_cfg.get("uri", ""),
            "user": neo4j_cfg.get("user", ""),
            "password": neo4j_cfg.get("password", ""),
            "database": neo4j_cfg.get("database", "neo4j"),
        }
    except Exception:
        return {}


def radar_chart(target_job: str, user_skills: list[str], result: dict) -> go.Figure:
    missing = {item["skill"] for item in result["skill_gap"]}
    labels = [item["skill"] for item in result["skill_gap"][:8]]
    if not labels:
        labels = user_skills[:8] or ["SQL", "Python", "Excel", "业务理解"]
    target_values = [1.0 for _ in labels]
    user_values = [0.0 if skill in missing else 1.0 for skill in labels]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=target_values + [target_values[0]], theta=labels + [labels[0]], fill="toself", name="岗位要求"))
    fig.add_trace(go.Scatterpolar(r=user_values + [user_values[0]], theta=labels + [labels[0]], fill="toself", name="当前技能"))
    fig.update_layout(title=f"{target_job} 技能匹配雷达图", polar=dict(radialaxis=dict(visible=True, range=[0, 1.1])), height=420)
    return fig


def salary_chart(salary_range: dict) -> go.Figure:
    salary_df = pd.DataFrame(
        {
            "type": ["min", "median", "max"],
            "salary": [salary_range["min"], salary_range["median"], salary_range["max"]],
        }
    )
    fig = px.bar(salary_df, x="type", y="salary", color="type", title="薪资预期区间", color_discrete_sequence=[BRAND_BLUE, BRAND_ORANGE, "#5c7c99"])
    fig.update_layout(showlegend=False, height=360, yaxis_title="CNY / month", xaxis_title="")
    return fig


def render_courses(courses: list[dict]) -> None:
    if not courses:
        st.info("当前技能差距较少，暂不需要课程推荐。")
        return
    for course in courses:
        skills = "、".join(course["skill_covered"])
        st.markdown(
            f"""
            <div class="course-card">
              <strong>{course['name']}</strong><br>
              平台：{course['platform']}<br>
              覆盖技能：{skills}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_similar_jobs(jobs: list[dict]) -> None:
    if not jobs:
        st.info("暂未找到相似岗位。")
        return
    cols = st.columns(min(4, len(jobs)))
    for idx, job in enumerate(jobs[:8]):
        with cols[idx % len(cols)]:
            st.markdown(
                f"""
                <div class="job-card">
                  <strong>{job['job_title']}</strong><br>
                  匹配度：{job['match_score']:.0%}
                </div>
                """,
                unsafe_allow_html=True,
            )


def main() -> None:
    st.set_page_config(page_title="职途智析", layout="wide")
    inject_css()
    st.markdown(
        """
        <div class="product-header">
          <h1>职途智析</h1>
          <p>输入目标岗位，发现你的技能差距</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1, 2])
    with left:
        st.subheader("输入信息")
        target_job = st.text_input("目标岗位", value="数据分析师", placeholder='如 "数据分析师"')
        skill_pool = available_skills()
        selected_skills = st.multiselect("当前技能", options=skill_pool, default=["Python", "Excel"], placeholder="搜索并选择技能")
        extra_skills = st.text_input("补充技能（逗号分隔）", placeholder="如 Wind, PPT")
        if extra_skills:
            selected_skills = selected_skills + [skill.strip() for skill in extra_skills.replace("，", ",").split(",") if skill.strip()]
        st.caption("第一版默认使用演示数据；配置 Neo4j secrets 后可切换真实后端。")
        submitted = st.button("开始分析", type="primary", use_container_width=True)

    with right:
        if not submitted:
            st.info("选择目标岗位和当前技能后，点击开始分析。")
            st.markdown("可选岗位：" + "、".join(available_jobs()))
            return
        if not target_job.strip():
            st.warning("请输入目标岗位。")
            return

        with st.spinner("正在分析技能差距、薪资区间和课程推荐..."):
            result = analyze_career(target_job, selected_skills, read_neo4j_config())

        mode_label = "真实后端模式" if result["mode"] == "neo4j" else "演示数据模式"
        st.markdown(f'<div class="mode-badge">{mode_label}</div>', unsafe_allow_html=True)

        if result["salary_range"]["median"] == 0 and not result["skill_gap"]:
            st.warning("暂未找到该岗位，请尝试输入：数据分析师、商业分析师、产品经理、证券研究员、投行分析师。")
            return

        metric_cols = st.columns(3)
        metric_cols[0].metric("缺口技能", len(result["skill_gap"]))
        metric_cols[1].metric("薪资中位数", f"{result['salary_range']['median']:,} 元/月")
        metric_cols[2].metric("相似岗位", len(result["similar_jobs"]))

        chart_cols = st.columns(2)
        with chart_cols[0]:
            st.plotly_chart(radar_chart(target_job, selected_skills, result), use_container_width=True)
        with chart_cols[1]:
            st.plotly_chart(salary_chart(result["salary_range"]), use_container_width=True)

        st.subheader("技能差距")
        gap_df = pd.DataFrame(result["skill_gap"])
        if gap_df.empty:
            st.success("当前技能已经覆盖该岗位的核心要求。")
        else:
            st.dataframe(gap_df, use_container_width=True)

        st.subheader("推荐课程")
        render_courses(result["recommended_courses"])

        st.subheader("相似岗位")
        render_similar_jobs(result["similar_jobs"])


if __name__ == "__main__":
    main()

