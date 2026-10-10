"""Unit tests for optional OpenAI AIReviewer with mocked API responses and error handling."""

import json
import unittest
from unittest.mock import MagicMock, patch
import openai
from bug_detector.ai.client import AIReviewer
from bug_detector.ai.models import AIReviewResult


class TestAIReviewer(unittest.TestCase):
    """Test suite for AI code review integration."""

    def test_missing_api_key_skips_cleanly(self):
        reviewer = AIReviewer(api_key="")
        self.assertFalse(reviewer.is_configured)
        result = reviewer.review("def test(): pass")
        self.assertEqual(result.status, "skipped")
        self.assertIn("not configured", result.error_message)
        self.assertEqual(len(result.findings), 0)

    def test_empty_source_code_skips(self):
        reviewer = AIReviewer(api_key="sk-test-mock-key")
        result = reviewer.review("   \n")
        self.assertEqual(result.status, "skipped")
        self.assertIn("Empty source code", result.error_message)

    def test_successful_mocked_ai_review(self):
        mock_response_data = {
            "code_quality_score": 85,
            "overall_summary": "Code is mostly functional but contains an off-by-one index issue.",
            "findings": [
                {
                    "line_number": 3,
                    "severity": "HIGH",
                    "issue": "Off-by-one loop indexing",
                    "explanation": "Iterating up to len(items) + 1 causes IndexError.",
                    "suggested_fix": "Use range(len(items)) or iterate directly over items.",
                }
            ],
            "refactored_code": "def process(items):\n    return [x * 2 for x in items]\n",
        }

        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(mock_response_data)
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        reviewer = AIReviewer(api_key="sk-test-mock-key", client=mock_client)
        result = reviewer.review("def process(items):\n    pass\n")

        self.assertEqual(result.status, "success")
        self.assertEqual(result.code_quality_score, 85)
        self.assertIn("off-by-one", result.overall_summary)
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(result.findings[0].severity, "HIGH")
        self.assertEqual(result.findings[0].line_number, 3)
        self.assertIsNotNone(result.refactored_code)

    def test_authentication_error_handling(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = openai.AuthenticationError(
            message="Incorrect API key provided",
            response=MagicMock(status_code=401),
            body=None,
        )

        reviewer = AIReviewer(api_key="sk-invalid-key", client=mock_client)
        result = reviewer.review("x = 1")
        self.assertEqual(result.status, "error")
        self.assertIn("Invalid OpenAI API key", result.error_message)

    def test_timeout_error_handling(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = openai.APITimeoutError(request=MagicMock())

        reviewer = AIReviewer(api_key="sk-test-key", client=mock_client)
        result = reviewer.review("x = 1")
        self.assertEqual(result.status, "error")
        self.assertIn("timed out", result.error_message)

    def test_rate_limit_error_handling(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = openai.RateLimitError(
            message="Rate limit reached",
            response=MagicMock(status_code=429),
            body=None,
        )

        reviewer = AIReviewer(api_key="sk-test-key", client=mock_client)
        result = reviewer.review("x = 1")
        self.assertEqual(result.status, "error")
        self.assertIn("rate limit", result.error_message.lower())

    def test_malformed_json_response_handling(self):
        mock_choice = MagicMock()
        mock_choice.message.content = "Not a json response {broken"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        reviewer = AIReviewer(api_key="sk-test-key", client=mock_client)
        result = reviewer.review("x = 1")
        self.assertEqual(result.status, "error")
        self.assertIn("malformed JSON", result.error_message)


if __name__ == "__main__":
    unittest.main()
