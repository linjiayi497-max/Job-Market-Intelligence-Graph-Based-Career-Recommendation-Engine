from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from career_service import analyze_career, available_jobs, available_projects, available_skills


class CareerServiceTest(unittest.TestCase):
    def test_available_catalogs_are_rich_enough_for_portfolio_demo(self) -> None:
        self.assertIn("数据分析师", available_jobs())
        self.assertIn("证券研究员", available_jobs())
        self.assertIn("SQL", available_skills())
        self.assertIn("Apache Superset", available_projects())
        self.assertGreaterEqual(len(available_jobs()), 35)
        self.assertGreaterEqual(len(available_projects()), 20)

    def test_analyze_returns_stable_schema(self) -> None:
        result = analyze_career("数据分析师", ["Python", "Excel"])
        self.assertEqual(
            set(result.keys()),
            {
                "target_job_profile",
                "skill_gap",
                "salary_range",
                "recommended_courses",
                "similar_jobs",
                "recommended_projects",
                "reference_projects",
                "interview_questions",
                "learning_plan",
                "mode",
            },
        )
        self.assertIn("median", result["salary_range"])
        self.assertEqual(result["mode"], "demo")
        self.assertEqual(result["recommended_projects"], [])
        self.assertGreaterEqual(len(result["reference_projects"]), 3)
        self.assertTrue(any(course.get("keywords") for course in result["recommended_courses"]))

    def test_empty_target_does_not_crash(self) -> None:
        result = analyze_career("", ["SQL"])
        self.assertEqual(result["salary_range"]["median"], 0)
        self.assertEqual(result["skill_gap"], [])
        self.assertEqual(result["recommended_projects"], [])
        self.assertEqual(result["reference_projects"], [])

    def test_unknown_target_returns_payload(self) -> None:
        result = analyze_career("完全不存在的岗位", ["SQL"])
        self.assertIn("similar_jobs", result)
        self.assertIn("recommended_courses", result)
        self.assertIn("recommended_projects", result)
        self.assertIn("reference_projects", result)

    def test_full_skill_match_has_no_gap_but_still_recommends_github_projects(self) -> None:
        skills = ["SQL", "Python", "Excel", "Tableau", "统计分析", "A/B测试", "业务理解", "数据可视化"]
        result = analyze_career("数据分析师", skills)
        self.assertEqual(result["skill_gap"], [])
        self.assertEqual(result["recommended_projects"], [])
        self.assertGreater(len(result["reference_projects"]), 0)

    def test_finance_role_recommends_quant_or_modeling_reference(self) -> None:
        result = analyze_career("量化研究助理", ["Excel", "Python", "Wind"])
        project_titles = [item["title"] for item in result["reference_projects"]]
        self.assertTrue(any(title in project_titles for title in ["Microsoft Qlib", "backtrader", "vn.py", "XGBoost"]))


if __name__ == "__main__":
    unittest.main()
