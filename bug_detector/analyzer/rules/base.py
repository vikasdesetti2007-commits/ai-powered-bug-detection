"""Base class and interface for modular AST static bug detection rules."""

import ast
from abc import ABC
from typing import List, Optional
from bug_detector.models import BugFinding, FindingCategory, Severity


class BaseRule(ast.NodeVisitor, ABC):
    """Abstract base class for all AST-based bug detection rules.
    
    Subclasses should define rule metadata (rule_id, name, category, severity, description)
    and implement one or more `visit_<NodeType>` methods.
    """
    rule_id: str
    name: str
    category: FindingCategory
    severity: Severity
    description: str

    def __init__(self, source_code: str = "") -> None:
        super().__init__()
        self.source_code = source_code
        self.source_lines = source_code.splitlines() if source_code else []
        self.findings: List[BugFinding] = []

    def get_line_snippet(self, line_no: int) -> Optional[str]:
        """Extract a single line snippet from the source code by 1-indexed line number."""
        if 1 <= line_no <= len(self.source_lines):
            return self.source_lines[line_no - 1].strip()
        return None

    def add_finding(
        self,
        node: ast.AST,
        message: str,
        suggestion: Optional[str] = None,
        severity_override: Optional[Severity] = None,
    ) -> None:
        """Helper to create and append a BugFinding from an AST node."""
        line_no = getattr(node, "lineno", 1)
        col_offset = getattr(node, "col_offset", 0)
        end_line_no = getattr(node, "end_lineno", line_no)
        end_col_offset = getattr(node, "end_col_offset", None)
        snippet = self.get_line_snippet(line_no)

        finding = BugFinding(
            rule_id=self.rule_id,
            rule_name=self.name,
            category=self.category,
            severity=severity_override or self.severity,
            message=message,
            line_number=line_no,
            column_offset=col_offset,
            end_line_number=end_line_no,
            end_column_offset=end_col_offset,
            suggestion=suggestion,
            code_snippet=snippet,
        )
        self.findings.append(finding)

    def analyze(self, tree: ast.AST) -> List[BugFinding]:
        """Execute the rule against an AST tree and return all detected findings."""
        self.findings = []
        self.visit(tree)
        return self.findings
