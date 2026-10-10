"""OpenAI API integration for intelligent code review."""

import json
from typing import Any, Dict, Optional
import openai
from bug_detector.ai.models import AIFinding, AIReviewResult
from bug_detector.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from bug_detector.config import settings


class AIReviewer:
    """Performs optional AI code review using the OpenAI API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 30.0,
        client: Optional[openai.OpenAI] = None,
    ) -> None:
        """Initialize the AI reviewer.
        
        Args:
            api_key: OpenAI API key. Defaults to settings.openai_api_key.
            model: Model name. Defaults to settings.openai_model.
            timeout: Request timeout in seconds.
            client: Optional injected OpenAI client instance (useful for mocking).
        """
        self._api_key = api_key if api_key is not None else settings.openai_api_key
        self.model = model if model is not None else settings.openai_model
        self.timeout = timeout
        self._client = client

    @property
    def is_configured(self) -> bool:
        """Check if an API key is present."""
        return bool(self._api_key and self._api_key.strip())

    def _get_client(self) -> openai.OpenAI:
        """Get or create the OpenAI client."""
        if self._client is not None:
            return self._client
        if not self.is_configured:
            raise ValueError("OpenAI API key is not configured.")
        return openai.OpenAI(api_key=self._api_key, timeout=self.timeout)

    def review(self, source_code: str) -> AIReviewResult:
        """Execute an AI review for the given Python code.
        
        Returns an AIReviewResult with status 'success', 'skipped', or 'error'.
        Guarantees that user source code is never executed.
        """
        if not self.is_configured and self._client is None:
            return AIReviewResult(
                status="skipped",
                error_message="OpenAI API key is not configured. Static analysis completed.",
            )

        if not source_code.strip():
            return AIReviewResult(
                status="skipped",
                error_message="Empty source code provided.",
            )

        try:
            client = self._get_client()
            user_content = build_user_prompt(source_code)

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            message_content = response.choices[0].message.content or "{}"
            raw_data: Dict[str, Any] = json.loads(message_content)

            findings_raw = raw_data.get("findings", [])
            findings = []
            for item in findings_raw:
                if isinstance(item, dict):
                    findings.append(
                        AIFinding(
                            line_number=item.get("line_number"),
                            severity=str(item.get("severity", "MEDIUM")).upper(),
                            issue=str(item.get("issue", "Issue")),
                            explanation=str(item.get("explanation", "")),
                            suggested_fix=str(item.get("suggested_fix", "")),
                        )
                    )

            score = raw_data.get("code_quality_score")
            if score is not None:
                try:
                    score = max(0, min(100, int(score)))
                except (ValueError, TypeError):
                    score = None

            return AIReviewResult(
                status="success",
                model_used=self.model,
                overall_summary=raw_data.get("overall_summary"),
                code_quality_score=score,
                findings=findings,
                refactored_code=raw_data.get("refactored_code"),
            )

        except openai.AuthenticationError:
            return AIReviewResult(
                status="error",
                error_message="Authentication failed: Invalid OpenAI API key.",
            )
        except openai.APITimeoutError:
            return AIReviewResult(
                status="error",
                error_message="OpenAI request timed out after 30 seconds.",
            )
        except openai.RateLimitError:
            return AIReviewResult(
                status="error",
                error_message="OpenAI API rate limit exceeded or quota exhausted.",
            )
        except openai.APIConnectionError:
            return AIReviewResult(
                status="error",
                error_message="Unable to connect to OpenAI API server.",
            )
        except json.JSONDecodeError as err:
            return AIReviewResult(
                status="error",
                error_message=f"Received malformed JSON from AI model: {err}",
            )
        except Exception as err:
            return AIReviewResult(
                status="error",
                error_message=f"AI review encountered an error: {type(err).__name__}",
            )
