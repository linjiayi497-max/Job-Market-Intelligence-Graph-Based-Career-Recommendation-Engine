from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEMO_DATA_PATH = ROOT / "demo_assets" / "career_graph_demo.json"
EXTENSION_DATA_PATH = ROOT / "demo_assets" / "career_extension_catalog.json"


def analyze_career(target_job: str, user_skills: list[str], neo4j_config: dict[str, str] | None = None) -> dict[str, Any]:
    """Return a stable career analysis payload for the product UI."""
    adapter: BaseCareerAdapter
    if _has_neo4j_config(neo4j_config):
        try:
            adapter = Neo4jCareerAdapter(neo4j_config or {})
            result = adapter.analyze(target_job, user_skills)
            result["mode"] = "neo4j"
            return result
        except Exception:
            adapter = DemoCareerAdapter()
    else:
        adapter = DemoCareerAdapter()
    result = adapter.analyze(target_job, user_skills)
    result["mode"] = "demo"
    return result


def available_skills() -> list[str]:
    data = _load_demo_data()
    skills = set()
    for job in data["jobs"]:
        skills.update(job["skills"].keys())
    return sorted(skills)


def available_jobs() -> list[str]:
    data = _load_demo_data()
    return [job["job_title"] for job in data["jobs"]]


def available_projects() -> list[str]:
    data = _load_demo_data()
    return [project["title"] for project in data.get("projects", [])]


class BaseCareerAdapter:
    def analyze(self, target_job: str, user_skills: list[str]) -> dict[str, Any]:
        raise NotImplementedError


class DemoCareerAdapter(BaseCareerAdapter):
    def __init__(self) -> None:
        self.data = _load_demo_data()

    def analyze(self, target_job: str, user_skills: list[str]) -> dict[str, Any]:
        normalized_user = {_normalize_skill(skill) for skill in user_skills if skill.strip()}
        job = self._find_job(target_job)
        if job is None:
            return _empty_payload(mode="demo")

        skill_gap = []
        for skill, importance in sorted(job["skills"].items(), key=lambda item: item[1], reverse=True):
            if _normalize_skill(skill) not in normalized_user:
                skill_gap.append({"skill": skill, "importance": round(float(importance), 4)})

        recommended_courses = self._recommend_courses([item["skill"] for item in skill_gap])
        similar_jobs = self._similar_jobs(job, normalized_user)
        recommended_projects = self._recommend_projects(job, normalized_user)
        reference_projects = self._recommend_reference_projects(job, normalized_user)
        interview_questions = self._interview_questions(job, skill_gap)
        learning_plan = self._learning_plan(skill_gap)
        salary = dict(job["salary"])
        salary.update({"currency": "CNY", "period": "month"})

        return {
            "target_job_profile": {
                "job_title": job["job_title"],
                "industry": job.get("industry", ""),
                "path": job.get("path", ""),
                "positioning": job.get("positioning", ""),
                "outputs": job.get("outputs", []),
            },
            "skill_gap": skill_gap,
            "salary_range": salary,
            "recommended_courses": recommended_courses,
            "similar_jobs": similar_jobs,
            "recommended_projects": recommended_projects,
            "reference_projects": reference_projects,
            "interview_questions": interview_questions,
            "learning_plan": learning_plan,
            "mode": "demo",
        }

    def _find_job(self, target_job: str) -> dict[str, Any] | None:
        keyword = target_job.strip().lower()
        if not keyword:
            return None
        jobs = self.data["jobs"]
        for job in jobs:
            if job["job_title"].lower() == keyword:
                return job
        for job in jobs:
            if keyword in job["job_title"].lower() or job["job_title"].lower() in keyword:
                return job
        return max(jobs, key=lambda job: _text_overlap(keyword, job["job_title"].lower()), default=None)

    def _recommend_courses(self, gap_skills: list[str]) -> list[dict[str, Any]]:
        gap_set = {_normalize_skill(skill) for skill in gap_skills}
        courses = []
        for course in self.data["courses"]:
            covered = [skill for skill in course["skills"] if _normalize_skill(skill) in gap_set]
            if covered:
                courses.append(
                    {
                        "name": course["name"],
                        "platform": course["platform"],
                        "skill_covered": covered,
                        "keywords": course.get("keywords", []),
                        "goal": course.get("goal", ""),
                        "deliverable": course.get("deliverable", ""),
                        "suitable_jobs": course.get("suitable_jobs", []),
                        "url": course.get("url", ""),
                    }
                )
        courses.sort(key=lambda item: (len(item["skill_covered"]), len(item.get("keywords", []))), reverse=True)
        return courses[:10]

    def _similar_jobs(self, target_job: dict[str, Any], normalized_user: set[str]) -> list[dict[str, Any]]:
        target_skills = {_normalize_skill(skill) for skill in target_job["skills"].keys()}
        rows = []
        for job in self.data["jobs"]:
            if job["job_title"] == target_job["job_title"]:
                continue
            job_skills = {_normalize_skill(skill) for skill in job["skills"].keys()}
            overlap = len(target_skills & job_skills)
            union = len(target_skills | job_skills) or 1
            user_bonus = len(job_skills & normalized_user) / max(len(job_skills), 1)
            score = 0.75 * (overlap / union) + 0.25 * user_bonus
            rows.append({"job_title": job["job_title"], "match_score": round(score, 4)})
        return sorted(rows, key=lambda item: item["match_score"], reverse=True)[:8]

    def _recommend_projects(self, target_job: dict[str, Any], normalized_user: set[str]) -> list[dict[str, Any]]:
        target_skills = {_normalize_skill(skill) for skill in target_job["skills"].keys()}
        target_title = target_job["job_title"]
        rows = []
        for project in self.data.get("projects", []):
            project_skills = {_normalize_skill(skill) for skill in project.get("skills", [])}
            suited_jobs = project.get("suited_jobs", [])
            title_bonus = 1.0 if target_title in suited_jobs else 0.0
            skill_overlap = len(target_skills & project_skills) / max(len(target_skills), 1)
            user_overlap = len(normalized_user & project_skills) / max(len(project_skills), 1)
            score = 0.5 * skill_overlap + 0.35 * title_bonus + 0.15 * user_overlap
            if score <= 0:
                continue
            rows.append(
                {
                    "title": project["title"],
                    "match_score": round(score, 4),
                    "summary": project.get("summary", ""),
                    "skills": project.get("skills", [])[:8],
                    "github_url": project.get("github_url", ""),
                    "live_url": project.get("live_url", ""),
                    "resume_pitch": project.get("resume_pitch", ""),
                    "match_reason": _project_reason(target_title, target_skills, project),
                }
            )
        return sorted(rows, key=lambda item: item["match_score"], reverse=True)[:8]

    def _recommend_reference_projects(self, target_job: dict[str, Any], normalized_user: set[str]) -> list[dict[str, Any]]:
        target_skills = {_normalize_skill(skill) for skill in target_job["skills"].keys()}
        target_title = target_job["job_title"]
        rows = []
        for project in self.data.get("reference_projects", []):
            project_skills = {_normalize_skill(skill) for skill in project.get("skills", [])}
            suited_jobs = project.get("suited_jobs", [])
            title_bonus = 1.0 if target_title in suited_jobs else 0.0
            skill_overlap = len(target_skills & project_skills) / max(len(target_skills), 1)
            user_overlap = len(normalized_user & project_skills) / max(len(project_skills), 1)
            score = 0.55 * skill_overlap + 0.35 * title_bonus + 0.10 * user_overlap
            if score <= 0:
                continue
            rows.append(
                {
                    "title": project["title"],
                    "match_score": round(score, 4),
                    "summary": project.get("summary", ""),
                    "skills": project.get("skills", [])[:8],
                    "github_url": project.get("github_url", ""),
                    "why_to_read": project.get("why_to_read", ""),
                    "match_reason": _project_reason(target_title, target_skills, project),
                }
            )
        return sorted(rows, key=lambda item: item["match_score"], reverse=True)[:10]

    def _interview_questions(self, target_job: dict[str, Any], skill_gap: list[dict[str, Any]]) -> list[str]:
        questions = list(target_job.get("questions", []))
        for item in skill_gap[:3]:
            questions.append(f"如果JD要求{item['skill']}，你会如何用自己的项目证明这个能力？")
        return questions[:8]

    def _learning_plan(self, skill_gap: list[dict[str, Any]]) -> list[str]:
        priority_skills = [item["skill"] for item in skill_gap[:3]]
        if not priority_skills:
            return ["当前技能覆盖度较高，建议重点准备项目复盘、业务影响和面试追问。"]
        templates = self.data.get("learning_templates", {}).get("default", [])
        focus = "、".join(priority_skills)
        return [line.replace("目标岗位最高权重的2-3个技能", f"{focus}") for line in templates]


class Neo4jCareerAdapter(BaseCareerAdapter):
    def __init__(self, config: dict[str, str]) -> None:
        from neo4j import GraphDatabase

        self.database = config.get("database", "neo4j")
        self.driver = GraphDatabase.driver(config["uri"], auth=(config["user"], config["password"]))

    def analyze(self, target_job: str, user_skills: list[str]) -> dict[str, Any]:
        demo_result = DemoCareerAdapter().analyze(target_job, user_skills)
        demo_result["mode"] = "neo4j"
        return demo_result


def _load_demo_data() -> dict[str, Any]:
    data = json.loads(DEMO_DATA_PATH.read_text(encoding="utf-8"))
    if EXTENSION_DATA_PATH.exists():
        extension = json.loads(EXTENSION_DATA_PATH.read_text(encoding="utf-8"))
        _merge_catalog(data, extension)
    return data


def _merge_catalog(base: dict[str, Any], extension: dict[str, Any]) -> None:
    for key, id_field in (("jobs", "job_title"), ("projects", "title"), ("reference_projects", "title")):
        existing = {item.get(id_field) for item in base.get(key, [])}
        for item in extension.get(key, []):
            if item.get(id_field) not in existing:
                base.setdefault(key, []).append(item)
                existing.add(item.get(id_field))

    base_courses = extension.get("courses", []) + base.get("courses", [])
    seen_courses = set()
    merged_courses = []
    for course in base_courses:
        name = course.get("name")
        if name in seen_courses:
            continue
        merged_courses.append(course)
        seen_courses.add(name)
    base["courses"] = merged_courses


def _has_neo4j_config(config: dict[str, str] | None) -> bool:
    if not config:
        return False
    return all(config.get(key) for key in ("uri", "user", "password"))


def _normalize_skill(skill: str) -> str:
    return skill.strip().lower().replace(" ", "")


def _text_overlap(left: str, right: str) -> int:
    return len(set(left) & set(right))


def _project_reason(target_title: str, target_skills: set[str], project: dict[str, Any]) -> str:
    overlap = [skill for skill in project.get("skills", []) if _normalize_skill(skill) in target_skills]
    if target_title in project.get("suited_jobs", []):
        return f"直接适配{target_title}，可作为该岗位的主打项目。"
    if overlap:
        return f"覆盖{target_title}常见要求：{'、'.join(overlap[:4])}。"
    return "可作为补充项目展示业务理解和数据产品能力。"


def _empty_payload(mode: str) -> dict[str, Any]:
    return {
        "target_job_profile": {"job_title": "", "industry": "", "path": "", "positioning": "", "outputs": []},
        "skill_gap": [],
        "salary_range": {"min": 0, "median": 0, "max": 0, "currency": "CNY", "period": "month"},
        "recommended_courses": [],
        "similar_jobs": [],
        "recommended_projects": [],
        "reference_projects": [],
        "interview_questions": [],
        "learning_plan": [],
        "mode": mode,
    }

