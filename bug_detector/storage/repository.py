"""Repository layer for persisting and retrieving review history in SQLite."""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from bug_detector.config import settings
from bug_detector.exceptions import StorageError
from bug_detector.models import (
    AnalysisReport,
    AnalysisSummary,
    BugFinding,
    ReviewRecord,
    SyntaxErrorInfo,
)
from bug_detector.storage.database import get_connection, init_db


class ReviewRepository:
    """Manages SQLite storage and querying of code review history."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None) -> None:
        """Initialize repository and ensure schema is ready.
        
        Args:
            db_path: Path to database file. Defaults to configured settings.db_path.
        """
        self.db_path = Path(db_path) if db_path is not None else settings.db_path
        init_db(self.db_path)

    @staticmethod
    def _compute_hash(source_code: str) -> str:
        """Calculate SHA-256 hex digest of source code."""
        return hashlib.sha256(source_code.encode("utf-8")).hexdigest()

    @staticmethod
    def _row_to_record(row: Any) -> ReviewRecord:
        """Convert a SQLite row to a ReviewRecord model, handling JSON safely."""
        try:
            syntax_err_data = json.loads(row["syntax_error_json"]) if row["syntax_error_json"] else None
            syntax_err = SyntaxErrorInfo.model_validate(syntax_err_data) if syntax_err_data else None

            findings_data = json.loads(row["findings_json"])
            findings = [BugFinding.model_validate(item) for item in findings_data]

            summary_data = json.loads(row["summary_json"])
            summary = AnalysisSummary.model_validate(summary_data)

            ai_data = json.loads(row["ai_review_json"]) if row["ai_review_json"] else None

            return ReviewRecord(
                id=row["id"],
                timestamp=row["created_at"],
                source_code=row["source_code"],
                code_hash=row["code_hash"],
                is_syntax_valid=bool(row["is_syntax_valid"]),
                syntax_error=syntax_err,
                findings=findings,
                summary=summary,
                ai_review=ai_data,
                duration_ms=float(row["duration_ms"]),
            )
        except (json.JSONDecodeError, ValueError, TypeError) as err:
            raise StorageError(f"Corrupted record data in review {row['id']}: {err}") from err

    def save_record(self, record: ReviewRecord) -> ReviewRecord:
        """Persist a ReviewRecord instance to SQLite using parameterized queries.
        
        Args:
            record: Fully populated ReviewRecord.
            
        Returns:
            The saved ReviewRecord.
        """
        syntax_err_json = record.syntax_error.model_dump_json() if record.syntax_error else None
        findings_json = json.dumps([f.model_dump() for f in record.findings])
        summary_json = record.summary.model_dump_json()
        ai_json = json.dumps(record.ai_review) if record.ai_review else None

        sql = """
        INSERT OR REPLACE INTO reviews (
            id, created_at, source_code, code_hash,
            is_syntax_valid, syntax_error_json, findings_json,
            summary_json, ai_review_json, duration_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                sql,
                (
                    record.id,
                    record.timestamp,
                    record.source_code,
                    record.code_hash,
                    1 if record.is_syntax_valid else 0,
                    syntax_err_json,
                    findings_json,
                    summary_json,
                    ai_json,
                    record.duration_ms,
                ),
            )
        return record

    def save_review(
        self,
        report: AnalysisReport,
        ai_review: Optional[Dict[str, Any]] = None,
        review_id: Optional[str] = None,
    ) -> ReviewRecord:
        """Convenience method to construct and save a ReviewRecord from an AnalysisReport.
        
        Args:
            report: AnalysisReport from the analyzer engine.
            ai_review: Optional AI review output dictionary.
            review_id: Optional custom ID. If omitted, generates a UUID4.
            
        Returns:
            Saved ReviewRecord.
        """
        record = ReviewRecord(
            id=review_id or str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            source_code=report.source_code,
            code_hash=self._compute_hash(report.source_code),
            is_syntax_valid=report.is_syntax_valid,
            syntax_error=report.syntax_error,
            findings=report.findings,
            summary=report.summary,
            ai_review=ai_review,
            duration_ms=report.execution_time_ms,
        )
        return self.save_record(record)

    def get_review_by_id(self, review_id: str) -> Optional[ReviewRecord]:
        """Retrieve a review record by its unique ID.
        
        Args:
            review_id: Unique string ID.
            
        Returns:
            ReviewRecord if found, else None.
        """
        sql = "SELECT * FROM reviews WHERE id = ?"
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (review_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_record(row)

    def list_recent_reviews(self, limit: int = 50, offset: int = 0) -> List[ReviewRecord]:
        """List reviews ordered by creation date descending.
        
        Args:
            limit: Maximum records to return.
            offset: Offset for pagination.
            
        Returns:
            List of ReviewRecord instances.
        """
        sql = "SELECT * FROM reviews ORDER BY created_at DESC LIMIT ? OFFSET ?"
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (max(1, limit), max(0, offset)))
            rows = cursor.fetchall()
            return [self._row_to_record(row) for row in rows]

    def search_reviews(
        self,
        query: Optional[str] = None,
        code_hash: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 50,
    ) -> List[ReviewRecord]:
        """Search reviews matching optional filters using parameterized SQL.
        
        Args:
            query: Substring search in source code.
            code_hash: Exact SHA-256 hash match.
            date_from: Minimum ISO timestamp (inclusive).
            date_to: Maximum ISO timestamp (inclusive).
            limit: Maximum records to return.
            
        Returns:
            List of matching ReviewRecord instances.
        """
        conditions: List[str] = []
        params: List[Any] = []

        if code_hash:
            conditions.append("code_hash = ?")
            params.append(code_hash)
        if date_from:
            conditions.append("created_at >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("created_at <= ?")
            params.append(date_to)
        if query:
            conditions.append("source_code LIKE ?")
            params.append(f"%{query}%")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM reviews {where_clause} ORDER BY created_at DESC LIMIT ?"
        params.append(max(1, limit))

        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
            return [self._row_to_record(row) for row in rows]

    def delete_review(self, review_id: str) -> bool:
        """Delete a review by ID.
        
        Args:
            review_id: ID of review to delete.
            
        Returns:
            True if row was deleted, False if ID not found.
        """
        sql = "DELETE FROM reviews WHERE id = ?"
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (review_id,))
            return cursor.rowcount > 0

    def clear_history(self) -> int:
        """Clear all stored reviews. Explicit action only.
        
        Returns:
            Number of deleted records.
        """
        sql = "DELETE FROM reviews"
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            return cursor.rowcount
