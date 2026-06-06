from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from career_service import analyze_career, available_jobs, available_skills


BRAND_BLUE = "#17324d"
BRAND_ORANGE = "#f28c28"
INK = "#0f1f33"
MUTED = "#5f6d7c"
DEMO_DATA_PATH = Path(__file__).resolve().parent / "demo_assets" / "career_graph_demo.json"


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
        .info-card, .course-card, .job-card, .project-card, .question-card {{
          background: white;
          border: 1px solid #e3e8ef;
          border-radius: 6px;
          padding: 12px 14px;
          margin-bottom: 10px;
          box-shadow: 0 2px 10px rgba(23, 50, 77, .05);
        }}
        .info-card strong, .course-card strong, .job-card strong, .project-card strong {{
          color: {BRAND_BLUE};
        }}
        .muted {{ color: {MUTED}; font-size: 13px; line-height: 1.5; }}
        .tag {{
          display: inline-block;
          background: #eef4fa;
          color: {INK};
          border-radius: 4px;
          padding: 3px 7px;
          margin: 2px 3px 2px 0;
          font-size: 12px;
        }}
        .link-line a {{ color: {BRAND_ORANGE}; text-decoration: none; }}
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


def available_projects() -> list[str]:
    try:
        data = json.loads(DEMO_DATA_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    return [project["title"] for project in data.get("projects", [])]


def ensure_result_schema(result: dict) -> dict:
    result.setdefault("target_job_profile", {"job_title": "", "industry": "", "path": "", "positioning": "", "outputs": []})
    result.setdefault("recommended_projects", [])
    result.setdefault("interview_questions", [])
    result.setdefault("learning_plan", [])
    result.setdefault("skill_gap", [])
    result.setdefault("recommended_courses", [])
    result.setdefault("similar_jobs", [])
    result.setdefault("salary_range", {"min": 0, "median": 0, "max": 0, "currency": "CNY", "period": "month"})
    result.setdefault("mode", "demo")
    return result


def radar_chart(target_job: str, user_skills: list[str], result: dict) -> go.Figure:
    missing = {item["skill"] for item in result["skill_gap"]}
    labels = [item["skill"] for item in result["skill_gap"][:8]]
    if not labels:
        labels = user_skills[:8] or ["SQL", "Python", "Excel", "业务理解"]
    target_values = [1.0 for _ in labels]
    user_values = [0.0 if skill in missing else 1.0 for skill in labels]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=target_values + [target_values[0]],
            theta=labels + [labels[0]],
            fill="toself",
            name="岗位要求",
            line_color=BRAND_BLUE,
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=user_values + [user_values[0]],
            theta=labels + [labels[0]],
            fill="toself",
            name="当前技能",
            line_color=BRAND_ORANGE,
        )
    )
    fig.update_layout(
        title=f"{target_job} 技能匹配雷达图",
        polar=dict(radialaxis=dict(visible=True, range=[0, 1.1])),
        height=420,
    )
    return fig


def salary_chart(salary_range: dict) -> go.Figure:
    salary_df = pd.DataFrame(
        {
            "type": ["min", "median", "max"],
            "salary": [salary_range["min"], salary_range["median"], salary_range["max"]],
        }
    )
    fig = px.bar(
        salary_df,
        x="type",
        y="salary",
        color="type",
        title="薪资预期区间",
        color_discrete_sequence=[BRAND_BLUE, BRAND_ORANGE, "#5c7c99"],
    )
    fig.update_layout(showlegend=False, height=360, yaxis_title="CNY / month", xaxis_title="")
    return fig


def render_profile(profile: dict) -> None:
    outputs = "、".join(profile.get("outputs", [])) or "岗位分析、项目复盘、业务汇报"
    st.markdown(
        f"""
        <div class="info-card">
          <strong>{html.escape(profile.get('job_title', '目标岗位'))}</strong>
          <div class="muted">{html.escape(profile.get('industry', ''))} · {html.escape(profile.get('path', ''))}</div>
          <p>{html.escape(profile.get('positioning', ''))}</p>
          <div class="muted">常见产出：{html.escape(outputs)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_courses(courses: list[dict]) -> None:
    if not courses:
        st.info("当前技能差距较少，暂不需要课程推荐。")
        return
    for course in courses:
        skills = "、".join(course["skill_covered"])
        st.markdown(
            f"""
            <div class="course-card">
              <strong>{html.escape(course['name'])}</strong><br>
              平台：{html.escape(course['platform'])}<br>
              覆盖技能：{html.escape(skills)}
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
                  <strong>{html.escape(job['job_title'])}</strong><br>
                  匹配度：{job['match_score']:.0%}
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_projects(projects: list[dict]) -> None:
    if not projects:
        st.info("暂未匹配到可展示项目。")
        return
    for project in projects:
        tags = "".join(f'<span class="tag">{html.escape(skill)}</span>' for skill in project.get("skills", [])[:8])
        links = []
        if project.get("github_url"):
            links.append(f'<a href="{html.escape(project["github_url"])}" target="_blank">GitHub</a>')
        if project.get("live_url"):
            links.append(f'<a href="{html.escape(project["live_url"])}" target="_blank">在线Demo</a>')
        link_line = " · ".join(links)
        st.markdown(
            f"""
            <div class="project-card">
              <strong>{html.escape(project['title'])}</strong>
              <div class="muted">匹配度：{project['match_score']:.0%} · {html.escape(project.get('match_reason', ''))}</div>
              <p>{html.escape(project.get('summary', ''))}</p>
              <div>{tags}</div>
              <p><strong>简历表述：</strong>{html.escape(project.get('resume_pitch', ''))}</p>
              <div class="link-line">{link_line}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_text_cards(title: str, items: list[str]) -> None:
    st.subheader(title)
    if not items:
        st.info("暂无内容。")
        return
    for item in items:
        st.markdown(f'<div class="question-card">{html.escape(item)}</div>', unsafe_allow_html=True)


def render_catalog_preview() -> None:
    jobs = available_jobs()
    projects = available_projects()
    skills = available_skills()
    stat_cols = st.columns(3)
    stat_cols[0].metric("岗位样例", len(jobs))
    stat_cols[1].metric("技能标签", len(skills))
    stat_cols[2].metric("项目素材", len(projects))

    st.markdown("可选岗位示例：")
    job_df = pd.DataFrame({"岗位": jobs})
    st.dataframe(job_df, use_container_width=True, height=270)

    st.markdown("已接入项目素材：")
    project_df = pd.DataFrame({"项目": projects})
    st.dataframe(project_df, use_container_width=True, height=230)


def main() -> None:
    st.set_page_config(page_title="职途智析", layout="wide")
    inject_css()
    st.markdown(
        """
        <div class="product-header">
          <h1>职途智析</h1>
          <p>输入目标岗位，发现技能差距、可补项目和面试准备重点</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1, 2])
    with left:
        st.subheader("输入信息")
        job_options = available_jobs()
        target_job = st.selectbox("目标岗位", options=job_options, index=0)
        custom_job = st.text_input("自定义岗位", placeholder='如"战略分析实习"')
        if custom_job.strip():
            target_job = custom_job.strip()

        skill_pool = available_skills()
        default_skills = [skill for skill in ["Python", "Excel"] if skill in skill_pool]
        selected_skills = st.multiselect("当前技能", options=skill_pool, default=default_skills, placeholder="搜索并选择技能")
        extra_skills = st.text_input("补充技能（逗号分隔）", placeholder="如 Wind, PPT")
        if extra_skills:
            selected_skills = selected_skills + [skill.strip() for skill in extra_skills.replace("，", ",").split(",") if skill.strip()]
        st.caption("第一版默认使用扩展演示数据；配置 Neo4j secrets 后可切换真实后端。")
        submitted = st.button("开始分析", type="primary", use_container_width=True)

    with right:
        if not submitted:
            st.info("选择目标岗位和当前技能后，点击开始分析。")
            render_catalog_preview()
            return

        if not target_job.strip():
            st.warning("请输入目标岗位。")
            return

        with st.spinner("正在分析技能差距、薪资区间、课程、项目和面试问题..."):
            result = ensure_result_schema(analyze_career(target_job, selected_skills, read_neo4j_config()))

        mode_label = "真实后端模式" if result["mode"] == "neo4j" else "扩展演示数据模式"
        st.markdown(f'<div class="mode-badge">{mode_label}</div>', unsafe_allow_html=True)

        if result["salary_range"]["median"] == 0 and not result["skill_gap"]:
            st.warning("暂未找到该岗位，请尝试输入：数据分析师、商业分析师、产品经理、证券研究员、投行分析师、增长运营。")
            return

        render_profile(result["target_job_profile"])

        metric_cols = st.columns(4)
        metric_cols[0].metric("缺口技能", len(result["skill_gap"]))
        metric_cols[1].metric("薪资中位数", f"{result['salary_range']['median']:,} 元/月")
        metric_cols[2].metric("相似岗位", len(result["similar_jobs"]))
        metric_cols[3].metric("推荐项目", len(result["recommended_projects"]))

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

        tab_projects, tab_courses, tab_jobs, tab_interview = st.tabs(["推荐项目", "推荐课程", "相似岗位", "面试准备"])
        with tab_projects:
            render_projects(result["recommended_projects"])
        with tab_courses:
            render_courses(result["recommended_courses"])
        with tab_jobs:
            render_similar_jobs(result["similar_jobs"])
        with tab_interview:
            render_text_cards("可能被追问的问题", result["interview_questions"])
            render_text_cards("学习与补强路径", result["learning_plan"])


if __name__ == "__main__":
    main()
