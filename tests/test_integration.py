"""End-to-end integration tests verifying cross-subsystem cooperation."""

import tempfile
import unittest
from pathlib import Path
from bug_detector.analyzer.engine import ASTAnalyzer
from bug_detector.models import Severity
from bug_detector.service import BugDetectionService
from bug_detector.storage.repository import ReviewRepository


class TestFullIntegration(unittest.TestCase):
    """End-to-end integration test suite."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "integration_history.db"
        self.service = BugDetectionService(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_full_pipeline_without_ai_key(self):
        """Verify entire pipeline functions properly when no OpenAI API key is configured."""
        code = (
            "def calculate_tax(amount, rates=[]):\n"
            "    if rates == None:\n"
            "        return 0\n"
            "    return amount * sum(rates)\n"
        )

        # 1. Analyze with request_ai=False
        record = self.service.analyze(source_code=code, request_ai=False, filename="tax.py")
        self.assertTrue(record.is_syntax_valid)
        self.assertIsNone(record.ai_review)
        self.assertEqual(len(record.findings), 2)
        # COR001 (mutable default) and COR002 (== None)
        rule_ids = {f.rule_id for f in record.findings}
        self.assertIn("COR001", rule_ids)
        self.assertIn("COR002", rule_ids)

        # 2. Retrieve from SQLite history
        retrieved = self.service.get_review(record.id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, record.id)
        self.assertEqual(retrieved.code_hash, record.code_hash)
        self.assertEqual(len(retrieved.findings), 2)

        # 3. Query history list
        history_list = self.service.list_history()
        self.assertEqual(len(history_list), 1)
        self.assertEqual(history_list[0].id, record.id)

        # 4. Search by hash
        search_res = self.service.search_history(code_hash=record.code_hash)
        self.assertEqual(len(search_res), 1)

    def test_non_execution_with_side_effects(self):
        """Verify that submitted code attempting filesystem writes is never executed."""
        canary_file = Path(self.temp_dir.name) / "canary.txt"
        self.assertFalse(canary_file.exists())

        # If executed, this Python code would create canary.txt
        malicious_code = f"with open('{canary_file}', 'w') as f:\n    f.write('pwned')\n"

        record = self.service.analyze(source_code=malicious_code, filename="untrusted.py")
        self.assertTrue(record.is_syntax_valid)

        # Confirm the canary file was NEVER created
        self.assertFalse(canary_file.exists(), "CRITICAL: Untrusted code was executed!")

    def test_syntax_error_pipeline(self):
        """Verify pipeline handles syntax errors safely and stores them in history."""
        broken_code = "for i in range(10\n    print(i)\n"
        record = self.service.analyze(source_code=broken_code, filename="broken.py")

        self.assertFalse(record.is_syntax_valid)
        self.assertIsNotNone(record.syntax_error)
        self.assertEqual(record.syntax_error.line_number, 1)

        # Check retrieval from DB
        from_db = self.service.get_review(record.id)
        self.assertIsNotNone(from_db)
        self.assertFalse(from_db.is_syntax_valid)
        self.assertIsNotNone(from_db.syntax_error)


if __name__ == "__main__":
    unittest.main()
