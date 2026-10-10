"""AST-based static code analysis engine.

Orchestrates syntax validation and modular rule evaluation without executing user code.
"""

import time
from typing import List, Optional, Type
from bug_detector.analyzer.rules import ALL_RULES, BaseRule
from bug_detector.analyzer.syntax_checker import check_syntax
from bug_detector.models import (
    AnalysisReport,
    AnalysisSummary,
    BugFinding,
    Severity,
)


class ASTAnalyzer:
    """Coordinator for static code analysis."""

    def __init__(self, rule_classes: Optional[List[Type[BaseRule]]] = None) -> None:
        """Initialize the analyzer with a list of rule classes.
        
        Args:
            rule_classes: Optional custom list of BaseRule subclasses.
                         Defaults to ALL_RULES.
        """
        self.rule_classes = rule_classes if rule_classes is not None else ALL_RULES

    def analyze(self, source_code: str, filename: str = "<input>") -> AnalysisReport:
        """Perform static analysis on the given Python source code.
        
        Guarantees that user source code is never executed.

        Args:
            source_code: The Python source code string to inspect.
            filename: Human-friendly name for reporting.

        Returns:
            AnalysisReport containing syntax validation state, any syntax errors,
            or static bug findings with summary statistics.
        """
        start_time = time.perf_counter()

        # Step 1: Check syntax
        is_valid, syntax_error, tree = check_syntax(source_code, filename=filename)

        if not is_valid or tree is None:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return AnalysisReport(
                source_code=source_code,
                is_syntax_valid=False,
                syntax_error=syntax_error,
                findings=[],
                summary=AnalysisSummary(
                    total_findings=1,
                    errors=1,
                    warnings=0,
                    info=0,
                    categories={"SYNTAX": 1},
                ),
                execution_time_ms=round(elapsed_ms, 2),
            )

        # Step 2: Run AST rules
        all_findings: List[BugFinding] = []
        for rule_cls in self.rule_classes:
            rule_instance = rule_cls(source_code=source_code)
            findings = rule_instance.analyze(tree)
            all_findings.extend(findings)

        # Step 3: Sort findings by line number, then column offset
        all_findings.sort(key=lambda f: (f.line_number, f.column_offset))

        # Step 4: Compute summary metrics
        summary = AnalysisSummary(
            total_findings=len(all_findings),
            errors=sum(1 for f in all_findings if f.severity == Severity.ERROR),
            warnings=sum(1 for f in all_findings if f.severity == Severity.WARNING),
            info=sum(1 for f in all_findings if f.severity == Severity.INFO),
        )
        for f in all_findings:
            cat_name = f.category.value
            summary.categories[cat_name] = summary.categories.get(cat_name, 0) + 1

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return AnalysisReport(
            source_code=source_code,
            is_syntax_valid=True,
            syntax_error=None,
            findings=all_findings,
            summary=summary,
            execution_time_ms=round(elapsed_ms, 2),
        )
