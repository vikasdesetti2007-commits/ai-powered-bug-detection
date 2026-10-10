"""AI-Powered Bug Detection System.

A modular static analysis and AI-assisted code review engine for Python.
"""

__version__ = "0.1.0"

from bug_detector.models import (
    BugFinding,
    FindingCategory,
    Severity,
    SyntaxErrorInfo,
    AnalysisReport,
    ReviewRecord,
)
from bug_detector.analyzer.engine import ASTAnalyzer
from bug_detector.analyzer.syntax_checker import check_syntax

__all__ = [
    "__version__",
    "BugFinding",
    "FindingCategory",
    "Severity",
    "SyntaxErrorInfo",
    "AnalysisReport",
    "ReviewRecord",
    "ASTAnalyzer",
    "check_syntax",
]
