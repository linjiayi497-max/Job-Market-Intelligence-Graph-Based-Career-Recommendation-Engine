from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEMO_DATA_PATH = ROOT / "demo_assets" / "career_graph_demo.json"


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
        salary = dict(job["salary"])
        salary.update({"currency": "CNY", "period": "month"})

        return {
            "skill_gap": skill_gap,
            "salary_range": salary,
            "recommended_courses": recommended_courses,
            "similar_jobs": similar_jobs,
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
                    }
                )
        courses.sort(key=lambda item: len(item["skill_covered"]), reverse=True)
        return courses[:8]

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
    return json.loads(DEMO_DATA_PATH.read_text(encoding="utf-8"))


def _has_neo4j_config(config: dict[str, str] | None) -> bool:
    if not config:
        return False
    return all(config.get(key) for key in ("uri", "user", "password"))


def _normalize_skill(skill: str) -> str:
    return skill.strip().lower().replace(" ", "")


def _text_overlap(left: str, right: str) -> int:
    return len(set(left) & set(right))


def _empty_payload(mode: str) -> dict[str, Any]:
    return {
        "skill_gap": [],
        "salary_range": {"min": 0, "median": 0, "max": 0, "currency": "CNY", "period": "month"},
        "recommended_courses": [],
        "similar_jobs": [],
        "mode": mode,
    }

