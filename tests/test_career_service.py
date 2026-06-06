from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from career_service import analyze_career, available_jobs, available_skills


class CareerServiceTest(unittest.TestCase):
    def test_available_catalogs(self) -> None:
        self.assertIn("数据分析师", available_jobs())
        self.assertIn("SQL", available_skills())

    def test_analyze_returns_stable_schema(self) -> None:
        result = analyze_career("数据分析师", ["Python", "Excel"])
        self.assertEqual(set(result.keys()), {"skill_gap", "salary_range", "recommended_courses", "similar_jobs", "mode"})
        self.assertIn("median", result["salary_range"])
        self.assertEqual(result["mode"], "demo")

    def test_empty_target_does_not_crash(self) -> None:
        result = analyze_career("", ["SQL"])
        self.assertEqual(result["salary_range"]["median"], 0)
        self.assertEqual(result["skill_gap"], [])

    def test_unknown_target_returns_payload(self) -> None:
        result = analyze_career("完全不存在的岗位", ["SQL"])
        self.assertIn("similar_jobs", result)
        self.assertIn("recommended_courses", result)

    def test_full_skill_match_has_no_gap(self) -> None:
        skills = ["SQL", "Python", "Excel", "Tableau", "统计分析", "A/B测试", "业务理解", "数据可视化"]
        result = analyze_career("数据分析师", skills)
        self.assertEqual(result["skill_gap"], [])


if __name__ == "__main__":
    unittest.main()

