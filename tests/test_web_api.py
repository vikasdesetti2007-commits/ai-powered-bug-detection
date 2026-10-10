"""Unit tests for FastAPI REST endpoints and web dashboard."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from bug_detector.ai.client import AIReviewer
from bug_detector.ai.models import AIFinding, AIReviewResult
from bug_detector.analyzer.engine import ASTAnalyzer
from bug_detector.service import BugDetectionService
from bug_detector.storage.repository import ReviewRepository
from bug_detector.web.app import create_app


class TestWebAPI(unittest.TestCase):
    """Test suite for FastAPI endpoints."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_api_history.db"

        # Mocked AI reviewer
        self.mock_ai_reviewer = MagicMock(spec=AIReviewer)
        self.mock_ai_reviewer.is_configured = True
        self.mock_ai_reviewer.model = "gpt-4o-mini"
        self.mock_ai_reviewer.review.return_value = AIReviewResult(
            status="success",
            model_used="gpt-4o-mini",
            overall_summary="Mocked AI review summary.",
            code_quality_score=92,
            findings=[
                AIFinding(
                    line_number=2,
                    severity="LOW",
                    issue="Minor naming improvement",
                    explanation="Variable could be clearer.",
                    suggested_fix="Rename x to counter.",
                )
            ],
            refactored_code="# Refactored code",
        )

        self.service = BugDetectionService(
            analyzer=ASTAnalyzer(),
            repository=ReviewRepository(db_path=self.db_path),
            ai_reviewer=self.mock_ai_reviewer,
        )
        self.app = create_app(service=self.service)
        self.client = TestClient(self.app)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_health_check_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["version"], "0.1.0")
        self.assertTrue(data["ai_configured"])
        self.assertEqual(data["model"], "gpt-4o-mini")
        # Ensure secret key is NEVER leaked in health response
        self.assertNotIn("api_key", data)
        self.assertNotIn("key", data)

    def test_analyze_clean_code(self):
        payload = {
            "source_code": "def hello():\n    return 'world'\n",
            "request_ai": False,
        }
        response = self.client.post("/api/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["is_syntax_valid"])
        self.assertIsNone(data["syntax_error"])
        self.assertEqual(len(data["findings"]), 0)
        self.assertIsNone(data["ai_review"])

    def test_analyze_syntax_error(self):
        payload = {
            "source_code": "def broken(\n    return 42",
            "request_ai": False,
        }
        response = self.client.post("/api/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["is_syntax_valid"])
        self.assertIsNotNone(data["syntax_error"])
        self.assertIn("broken(", data["syntax_error"]["line_text"])

    def test_analyze_with_ai_review(self):
        payload = {
            "source_code": "x = 10\n",
            "request_ai": True,
        }
        response = self.client.post("/api/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsNotNone(data["ai_review"])
        self.assertEqual(data["ai_review"]["status"], "success")
        self.assertEqual(data["ai_review"]["code_quality_score"], 92)

    def test_history_crud_endpoints(self):
        # 1. Analyze two records
        self.client.post("/api/analyze", json={"source_code": "a = 1\n"})
        res2 = self.client.post("/api/analyze", json={"source_code": "b = 2\n"})
        record2_id = res2.json()["id"]

        # 2. List history
        hist_res = self.client.get("/api/history?limit=10")
        self.assertEqual(hist_res.status_code, 200)
        items = hist_res.json()
        self.assertEqual(len(items), 2)

        # 3. Get single review
        single_res = self.client.get(f"/api/history/{record2_id}")
        self.assertEqual(single_res.status_code, 200)
        self.assertEqual(single_res.json()["id"], record2_id)

        # 4. Get non-existent review
        notFound_res = self.client.get("/api/history/non-existent-id-12345")
        self.assertEqual(notFound_res.status_code, 404)

        # 5. Delete review
        del_res = self.client.delete(f"/api/history/{record2_id}")
        self.assertEqual(del_res.status_code, 200)
        self.assertTrue(del_res.json()["success"])

        # Subsequent get returns 404
        self.assertEqual(self.client.get(f"/api/history/{record2_id}").status_code, 404)

        # 6. Clear history
        clear_res = self.client.post("/api/history/clear")
        self.assertEqual(clear_res.status_code, 200)
        self.assertEqual(clear_res.json()["cleared_count"], 1)

        # History should now be empty
        self.assertEqual(len(self.client.get("/api/history").json()), 0)

    def test_serve_dashboard_index(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("AI-Powered Bug Detection System", response.text)


if __name__ == "__main__":
    unittest.main()
