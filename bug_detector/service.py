"""Unified service coordinator connecting static analysis, AI review, and persistence."""

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from bug_detector.ai.client import AIReviewer
from bug_detector.analyzer.engine import ASTAnalyzer
from bug_detector.models import AnalysisReport, ReviewRecord
from bug_detector.storage.repository import ReviewRepository


class BugDetectionService:
    """High-level service orchestrating analysis, AI review, and persistence."""

    def __init__(
        self,
        analyzer: Optional[ASTAnalyzer] = None,
        repository: Optional[ReviewRepository] = None,
        ai_reviewer: Optional[AIReviewer] = None,
        db_path: Optional[Union[str, Path]] = None,
    ) -> None:
        self.analyzer = analyzer or ASTAnalyzer()
        self.repository = repository or ReviewRepository(db_path=db_path)
        self.ai_reviewer = ai_reviewer or AIReviewer()

    def analyze(
        self,
        source_code: str,
        request_ai: bool = False,
        filename: str = "<input>",
        save: bool = True,
    ) -> ReviewRecord:
        """Run analysis on source code, optionally run AI review, and persist record.
        
        Guarantees that user source code is never executed.
        """
        # Step 1: Static analysis
        report = self.analyzer.analyze(source_code, filename=filename)

        # Step 2: Optional AI review (only if requested and syntax is valid)
        ai_payload: Optional[Dict[str, Any]] = None
        if request_ai and report.is_syntax_valid:
            ai_result = self.ai_reviewer.review(source_code)
            ai_payload = ai_result.model_dump()

        # Step 3: Persist or build record
        if save:
            return self.repository.save_review(report, ai_review=ai_payload)

        # Build in-memory record if save=False
        code_hash = hashlib.sha256(source_code.encode("utf-8")).hexdigest()
        return ReviewRecord(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            source_code=source_code,
            code_hash=code_hash,
            is_syntax_valid=report.is_syntax_valid,
            syntax_error=report.syntax_error,
            findings=report.findings,
            summary=report.summary,
            ai_review=ai_payload,
            duration_ms=report.execution_time_ms,
        )

    def get_review(self, review_id: str) -> Optional[ReviewRecord]:
        return self.repository.get_review_by_id(review_id)

    def list_history(self, limit: int = 50, offset: int = 0) -> List[ReviewRecord]:
        return self.repository.list_recent_reviews(limit=limit, offset=offset)

    def search_history(
        self,
        query: Optional[str] = None,
        code_hash: Optional[str] = None,
        limit: int = 50,
    ) -> List[ReviewRecord]:
        return self.repository.search_reviews(query=query, code_hash=code_hash, limit=limit)

    def delete_review(self, review_id: str) -> bool:
        return self.repository.delete_review(review_id)

    def clear_history(self) -> int:
        return self.repository.clear_history()
