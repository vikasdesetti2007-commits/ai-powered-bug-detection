"""FastAPI web application exposing REST APIs and modern web dashboard."""

from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from bug_detector.config import settings
from bug_detector.models import ReviewRecord
from bug_detector.service import BugDetectionService

STATIC_DIR = Path(__file__).resolve().parent / "static"


class AnalyzeRequest(BaseModel):
    """Payload for code analysis."""
    source_code: str = Field(..., description="Python source code to analyze")
    request_ai: bool = Field(False, description="Flag indicating whether to trigger AI review")
    filename: Optional[str] = Field("<web-input>", description="Optional filename identifier")
    save: bool = Field(True, description="Whether to persist the review in SQLite history")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    ai_configured: bool
    model: str
    database_connected: bool


def create_app(service: Optional[BugDetectionService] = None) -> FastAPI:
    """Application factory for FastAPI instance."""
    app = FastAPI(
        title="AI-Powered Bug Detection System",
        description="Static Python AST bug analysis with optional AI review and history tracking.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Use provided service or default instance
    app_service = service or BugDetectionService()

    @app.get("/api/health", response_model=HealthResponse)
    def health_check() -> HealthResponse:
        """System health and capabilities check. Never leaks secrets."""
        return HealthResponse(
            status="healthy",
            version="0.1.0",
            ai_configured=app_service.ai_reviewer.is_configured,
            model=app_service.ai_reviewer.model,
            database_connected=True,
        )

    @app.post("/api/analyze", response_model=ReviewRecord)
    def analyze_code(payload: AnalyzeRequest) -> ReviewRecord:
        """Analyze submitted Python source code statically and optionally with AI.
        
        Guarantees that user source code is never executed.
        """
        try:
            return app_service.analyze(
                source_code=payload.source_code,
                request_ai=payload.request_ai,
                filename=payload.filename or "<web-input>",
                save=payload.save,
            )
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Analysis failed: {err}",
            )

    @app.get("/api/history", response_model=List[ReviewRecord])
    def get_history(
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        query: Optional[str] = Query(None),
        code_hash: Optional[str] = Query(None),
    ) -> List[ReviewRecord]:
        """Fetch review history with pagination or optional search filters."""
        try:
            if query or code_hash:
                return app_service.search_history(query=query, code_hash=code_hash, limit=limit)
            return app_service.list_history(limit=limit, offset=offset)
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to query history: {err}",
            )

    @app.get("/api/history/{review_id}", response_model=ReviewRecord)
    def get_history_detail(review_id: str) -> ReviewRecord:
        """Retrieve a specific review record by its ID."""
        record = app_service.get_review(review_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review record '{review_id}' not found.",
            )
        return record

    @app.delete("/api/history/{review_id}")
    def delete_history_item(review_id: str) -> Dict[str, Any]:
        """Delete an individual review record."""
        deleted = app_service.delete_review(review_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review record '{review_id}' not found.",
            )
        return {"success": True, "id": review_id, "message": "Review deleted."}

    @app.post("/api/history/clear")
    def clear_history() -> Dict[str, Any]:
        """Explicitly clear all stored reviews."""
        count = app_service.clear_history()
        return {"success": True, "cleared_count": count, "message": "History cleared."}

    # Mount static assets if static folder exists
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

        @app.get("/", include_in_schema=False)
        def serve_index() -> FileResponse:
            index_path = STATIC_DIR / "index.html"
            if index_path.exists():
                return FileResponse(index_path)
            raise HTTPException(status_code=404, detail="Index page not found.")

    return app


# Default app instance for ASGI servers like uvicorn
app = create_app()
