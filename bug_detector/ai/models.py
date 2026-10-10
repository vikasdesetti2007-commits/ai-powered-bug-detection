"""Data models for optional AI code review."""

from typing import List, Optional
from pydantic import BaseModel, Field


class AIFinding(BaseModel):
    """An issue identified by the AI code review."""
    line_number: Optional[int] = Field(None, description="Line number if applicable")
    severity: str = Field("MEDIUM", description="Severity level: HIGH, MEDIUM, LOW, INFO")
    issue: str = Field(..., description="Short description of the issue")
    explanation: str = Field(..., description="In-depth explanation of why this is problematic")
    suggested_fix: str = Field(..., description="Recommended code fix or pattern")


class AIReviewResult(BaseModel):
    """Result of an AI code review."""
    status: str = Field(..., description="Status: 'success', 'skipped', or 'error'")
    model_used: Optional[str] = Field(None, description="OpenAI model identifier used")
    overall_summary: Optional[str] = Field(None, description="Executive summary of code quality")
    code_quality_score: Optional[int] = Field(None, ge=0, le=100, description="Score from 0 to 100")
    findings: List[AIFinding] = Field(default_factory=list, description="List of AI detected findings")
    refactored_code: Optional[str] = Field(None, description="Complete suggested refactored code")
    error_message: Optional[str] = Field(None, description="Error message if review failed or skipped")
