"""Unit tests for SQLite database persistence and repository layer."""

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from bug_detector.analyzer.engine import ASTAnalyzer
from bug_detector.exceptions import StorageError
from bug_detector.models import (
    AnalysisReport,
    AnalysisSummary,
    BugFinding,
    FindingCategory,
    ReviewRecord,
    Severity,
)
from bug_detector.storage.database import ensure_db_directory, init_db
from bug_detector.storage.repository import ReviewRepository


class TestStorage(unittest.TestCase):
    """Test suite for SQLite database and ReviewRepository."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_history.db"
        self.repo = ReviewRepository(db_path=self.db_path)
        self.analyzer = ASTAnalyzer()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_database_auto_initialization(self):
        # Nested directory that does not exist yet
        nested_db = Path(self.temp_dir.name) / "deep" / "nested" / "dir" / "history.db"
        self.assertFalse(nested_db.parent.exists())

        init_db(nested_db)
        self.assertTrue(nested_db.exists())

        with sqlite3.connect(str(nested_db)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reviews'")
            self.assertIsNotNone(cursor.fetchone())

            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_reviews_code_hash'")
            self.assertIsNotNone(cursor.fetchone())

    def test_save_and_retrieve_review(self):
        code = "def add(a, b):\n    return a + b\n"
        report = self.analyzer.analyze(code)

        saved = self.repo.save_review(report)
        self.assertIsNotNone(saved.id)
        self.assertEqual(saved.source_code, code)
        self.assertTrue(saved.is_syntax_valid)
        self.assertIsNone(saved.ai_review)
        self.assertGreater(len(saved.code_hash), 0)

        retrieved = self.repo.get_review_by_id(saved.id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, saved.id)
        self.assertEqual(retrieved.code_hash, saved.code_hash)
        self.assertEqual(retrieved.source_code, saved.source_code)
        self.assertTrue(retrieved.is_syntax_valid)
        self.assertEqual(len(retrieved.findings), 0)

    def test_save_and_retrieve_syntax_error_review(self):
        bad_code = "def broken(x\n    return x\n"
        report = self.analyzer.analyze(bad_code)

        saved = self.repo.save_review(report)
        self.assertFalse(saved.is_syntax_valid)
        self.assertIsNotNone(saved.syntax_error)

        retrieved = self.repo.get_review_by_id(saved.id)
        self.assertIsNotNone(retrieved)
        self.assertFalse(retrieved.is_syntax_valid)
        self.assertIsNotNone(retrieved.syntax_error)
        self.assertIn("broken(x", retrieved.syntax_error.line_text)

    def test_save_with_optional_ai_review(self):
        code = "x = 10\n"
        report = self.analyzer.analyze(code)
        ai_payload = {"summary": "Clean code", "score": 98}

        saved = self.repo.save_review(report, ai_review=ai_payload)
        retrieved = self.repo.get_review_by_id(saved.id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.ai_review, ai_payload)

    def test_list_recent_reviews_and_pagination(self):
        for i in range(5):
            code = f"x = {i}\n"
            report = self.analyzer.analyze(code)
            self.repo.save_review(report)

        # Page 1: limit 3
        page1 = self.repo.list_recent_reviews(limit=3, offset=0)
        self.assertEqual(len(page1), 3)

        # Page 2: limit 3, offset 3
        page2 = self.repo.list_recent_reviews(limit=3, offset=3)
        self.assertEqual(len(page2), 2)

        # Ensure unique IDs across pages
        ids_p1 = {r.id for r in page1}
        ids_p2 = {r.id for r in page2}
        self.assertTrue(ids_p1.isdisjoint(ids_p2))

    def test_search_by_code_hash(self):
        code = "magic_number = 42\n"
        report = self.analyzer.analyze(code)
        saved = self.repo.save_review(report)

        results = self.repo.search_reviews(code_hash=saved.code_hash)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, saved.id)

        # Non-matching hash
        empty = self.repo.search_reviews(code_hash="nonexistenthash123")
        self.assertEqual(len(empty), 0)

    def test_search_by_query_substring(self):
        code1 = "def target_function_alpha(): pass"
        code2 = "def other_function(): pass"
        self.repo.save_review(self.analyzer.analyze(code1))
        self.repo.save_review(self.analyzer.analyze(code2))

        matches = self.repo.search_reviews(query="target_function_alpha")
        self.assertEqual(len(matches), 1)
        self.assertIn("target_function_alpha", matches[0].source_code)

    def test_search_by_date_range(self):
        code = "print('hello')"
        saved = self.repo.save_review(self.analyzer.analyze(code))

        matches = self.repo.search_reviews(date_from="2020-01-01T00:00:00", date_to="2099-01-01T00:00:00")
        self.assertGreaterEqual(len(matches), 1)

        past = self.repo.search_reviews(date_from="2010-01-01T00:00:00", date_to="2010-01-02T00:00:00")
        self.assertEqual(len(past), 0)

    def test_delete_review(self):
        code = "val = 1\n"
        saved = self.repo.save_review(self.analyzer.analyze(code))

        # Delete existing
        deleted = self.repo.delete_review(saved.id)
        self.assertTrue(deleted)
        self.assertIsNone(self.repo.get_review_by_id(saved.id))

        # Delete non-existing
        deleted_again = self.repo.delete_review("nonexistent-id")
        self.assertFalse(deleted_again)

    def test_clear_history(self):
        for i in range(4):
            self.repo.save_review(self.analyzer.analyze(f"v = {i}\n"))

        self.assertEqual(len(self.repo.list_recent_reviews()), 4)

        cleared_count = self.repo.clear_history()
        self.assertEqual(cleared_count, 4)
        self.assertEqual(len(self.repo.list_recent_reviews()), 0)

    def test_malformed_json_error_handling(self):
        # Directly insert a row with corrupt findings_json
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO reviews (
                    id, created_at, source_code, code_hash,
                    is_syntax_valid, syntax_error_json, findings_json,
                    summary_json, ai_review_json, duration_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "corrupt-1",
                    "2026-10-10T12:00:00Z",
                    "x = 1",
                    "hash123",
                    1,
                    None,
                    "{corrupted invalid json",
                    "{}",
                    None,
                    1.5,
                ),
            )

        # get_review_by_id should safely catch the corruption and raise StorageError
        with self.assertRaises(StorageError):
            self.repo.get_review_by_id("corrupt-1")

    def test_database_error_handling_invalid_directory(self):
        # Attempt to initialize in an invalid path (e.g. file exists where directory should be)
        blocking_file = Path(self.temp_dir.name) / "file_blocking_dir"
        blocking_file.write_text("not a directory")
        invalid_db_path = blocking_file / "subdir" / "db.sqlite3"

        with self.assertRaises(StorageError):
            init_db(invalid_db_path)


if __name__ == "__main__":
    unittest.main()
