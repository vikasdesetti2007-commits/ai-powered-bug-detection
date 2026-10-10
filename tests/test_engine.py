"""Unit tests for ASTAnalyzer coordination and reporting."""

import unittest
from bug_detector.analyzer.engine import ASTAnalyzer
from bug_detector.models import Severity


class TestASTAnalyzerEngine(unittest.TestCase):
    """Test suite for top-level ASTAnalyzer engine."""

    def setUp(self):
        self.analyzer = ASTAnalyzer()

    def test_clean_python_code_analysis(self):
        code = (
            "def calculate_total(prices: list[float]) -> float:\n"
            "    total = 0.0\n"
            "    for price in prices:\n"
            "        total += price\n"
            "    return total\n"
        )
        report = self.analyzer.analyze(code)
        self.assertTrue(report.is_syntax_valid)
        self.assertIsNone(report.syntax_error)
        self.assertEqual(len(report.findings), 0)
        self.assertEqual(report.summary.total_findings, 0)
        self.assertGreaterEqual(report.execution_time_ms, 0.0)

    def test_syntax_error_short_circuits(self):
        code = "def broken(\n    return 42"
        report = self.analyzer.analyze(code)
        self.assertFalse(report.is_syntax_valid)
        self.assertIsNotNone(report.syntax_error)
        self.assertEqual(len(report.findings), 0)
        self.assertEqual(report.summary.errors, 1)
        self.assertEqual(report.summary.categories.get("SYNTAX"), 1)

    def test_multi_rule_detection_and_sorting(self):
        code = (
            "# Line 1\n"
            "def process(items=[], id=0):\n"  # COR001 (mutable default), STY002 (shadowed id)
            "    if items == None:\n"          # COR002 (identity comparison)
            "        return 1 / 0\n"           # COR003 (division by zero)
            "        print('unreachable')\n"   # COR005 (unreachable code)
            "    return 42\n"
        )
        report = self.analyzer.analyze(code)
        self.assertTrue(report.is_syntax_valid)
        self.assertGreaterEqual(len(report.findings), 4)

        # Ensure findings are sorted by line number
        line_numbers = [f.line_number for f in report.findings]
        self.assertEqual(line_numbers, sorted(line_numbers))

        # Check summary counts
        self.assertGreater(report.summary.total_findings, 0)
        self.assertEqual(report.summary.total_findings, len(report.findings))

    def test_non_execution_guarantee(self):
        """Ensure code with destructive statements is never executed."""
        # If this code were executed, it would raise SystemExit or ZeroDivisionError
        dangerous_code = "import sys\nsys.exit(99)\n1 / 0\n"
        report = self.analyzer.analyze(dangerous_code)
        self.assertTrue(report.is_syntax_valid)
        # Verify it safely analyzed without exiting Python process
        self.assertTrue(any(f.rule_id == "COR003" for f in report.findings))

    def test_report_serialization(self):
        code = "x = 1 / 0\n"
        report = self.analyzer.analyze(code)
        report_dict = report.model_dump()
        self.assertIn("findings", report_dict)
        self.assertIn("summary", report_dict)
        self.assertIn("is_syntax_valid", report_dict)
        self.assertEqual(report_dict["summary"]["errors"], 1)


if __name__ == "__main__":
    unittest.main()
