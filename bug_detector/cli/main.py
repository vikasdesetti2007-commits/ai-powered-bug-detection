"""Command-line interface for the AI-Powered Bug Detection System."""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional
from bug_detector.service import BugDetectionService

# ANSI color codes for terminal polish
COLOR_RESET = "\033[0m"
COLOR_RED = "\033[91m"
COLOR_YELLOW = "\033[93m"
COLOR_BLUE = "\033[94m"
COLOR_GREEN = "\033[92m"
COLOR_BOLD = "\033[1m"
COLOR_GRAY = "\033[90m"


def format_severity(severity: str) -> str:
    sev = severity.upper()
    if sev == "ERROR" or sev == "HIGH":
        return f"{COLOR_RED}{COLOR_BOLD}[{sev}]{COLOR_RESET}"
    elif sev == "WARNING" or sev == "MEDIUM":
        return f"{COLOR_YELLOW}{COLOR_BOLD}[{sev}]{COLOR_RESET}"
    elif sev == "INFO" or sev == "LOW":
        return f"{COLOR_BLUE}{COLOR_BOLD}[{sev}]{COLOR_RESET}"
    return f"{COLOR_BOLD}[{sev}]{COLOR_RESET}"


def run_cli(args: argparse.Namespace) -> int:
    service = BugDetectionService(db_path=args.db_path)

    # Action 1: Clear history
    if args.clear_history:
        count = service.clear_history()
        print(f"{COLOR_GREEN}Successfully cleared {count} records from review history.{COLOR_RESET}")
        return 0

    # Action 2: View history
    if args.history:
        reviews = service.list_history(limit=args.history_limit)
        if not reviews:
            print(f"{COLOR_GRAY}No past reviews recorded.{COLOR_RESET}")
            return 0
        print(f"\n{COLOR_BOLD}=== Review History (Latest {len(reviews)}) ==={COLOR_RESET}\n")
        for r in reviews:
            status = f"{COLOR_GREEN}VALID{COLOR_RESET}" if r.is_syntax_valid else f"{COLOR_RED}SYNTAX ERROR{COLOR_RESET}"
            issues = f"{r.summary.total_findings} findings"
            ai_status = f", AI: {r.ai_review.get('status')}" if r.ai_review else ""
            print(f"- {COLOR_BOLD}{r.id[:8]}{COLOR_RESET} [{r.timestamp[:19]}] {status} | {issues}{ai_status}")
            snippet = r.source_code.strip().splitlines()[0] if r.source_code.strip() else "(empty)"
            print(f"  {COLOR_GRAY}{snippet[:60]}...{COLOR_RESET}")
        print()
        return 0

    # Action 3: Analyze file / stdin
    if not args.file:
        print(f"{COLOR_RED}Error: Please specify a Python file to analyze, or use --history.{COLOR_RESET}", file=sys.stderr)
        return 1

    source_code = ""
    filename = args.file

    if args.file == "-":
        filename = "<stdin>"
        source_code = sys.stdin.read()
    else:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"{COLOR_RED}Error: File not found: '{args.file}'{COLOR_RESET}", file=sys.stderr)
            return 1
        if file_path.is_dir():
            print(f"{COLOR_RED}Error: Target '{args.file}' is a directory. Please specify a Python file.{COLOR_RESET}", file=sys.stderr)
            return 1
        try:
            source_code = file_path.read_text(encoding="utf-8")
        except Exception as err:
            print(f"{COLOR_RED}Error reading file '{args.file}': {err}{COLOR_RESET}", file=sys.stderr)
            return 1

    # Run analysis
    record = service.analyze(
        source_code=source_code,
        request_ai=args.ai,
        filename=filename,
        save=not args.no_save,
    )

    # JSON output requested
    if args.json:
        print(json.dumps(record.model_dump(), indent=2))
        return 0 if (record.is_syntax_valid and record.summary.errors == 0) else 1

    # Formatted terminal output
    print(f"\n{COLOR_BOLD}=== Static Code Analysis: {filename} ==={COLOR_RESET}")
    print(f"SHA-256: {COLOR_GRAY}{record.code_hash[:16]}...{COLOR_RESET} | Duration: {record.duration_ms:.1f}ms")

    # Check syntax error
    if not record.is_syntax_valid and record.syntax_error:
        err = record.syntax_error
        print(f"\n{COLOR_RED}{COLOR_BOLD}[SYNTAX ERROR] Line {err.line_number}:{err.column_offset}{COLOR_RESET}")
        print(f"Message: {err.message}")
        if err.pointer_diagram:
            print(f"\n{err.pointer_diagram}\n")
        return 1

    # Static findings
    if not record.findings:
        print(f"\n{COLOR_GREEN}✓ No static bugs detected! Code passed all AST rules.{COLOR_RESET}")
    else:
        print(f"\n{COLOR_BOLD}Detected Issues ({len(record.findings)}):{COLOR_RESET}")
        for i, finding in enumerate(record.findings, 1):
            sev_badge = format_severity(finding.severity.value)
            print(f"\n  {i}. {sev_badge} {COLOR_BOLD}{finding.rule_id}: {finding.rule_name}{COLOR_RESET}")
            print(f"     Location: Line {finding.line_number}:{finding.column_offset}")
            if finding.code_snippet:
                print(f"     Code: {COLOR_GRAY}{finding.code_snippet}{COLOR_RESET}")
            print(f"     Issue: {finding.message}")
            if finding.suggestion:
                print(f"     Suggestion: {COLOR_GREEN}{finding.suggestion}{COLOR_RESET}")

    # Summary bar
    s = record.summary
    print(f"\n{COLOR_BOLD}Summary:{COLOR_RESET} {s.total_findings} total ({COLOR_RED}{s.errors} errors{COLOR_RESET}, {COLOR_YELLOW}{s.warnings} warnings{COLOR_RESET}, {COLOR_BLUE}{s.info} info{COLOR_RESET})")

    # AI review section
    if record.ai_review:
        ai = record.ai_review
        print(f"\n{COLOR_BOLD}=== AI Code Review ({ai.get('model_used', 'OpenAI')}) ==={COLOR_RESET}")
        if ai.get("status") == "skipped":
            print(f"{COLOR_YELLOW}AI Review Skipped: {ai.get('error_message')}{COLOR_RESET}")
        elif ai.get("status") == "error":
            print(f"{COLOR_RED}AI Review Error: {ai.get('error_message')}{COLOR_RESET}")
        elif ai.get("status") == "success":
            score = ai.get("code_quality_score")
            score_str = f"{score}/100" if score is not None else "N/A"
            print(f"Quality Score: {COLOR_BOLD}{score_str}{COLOR_RESET}")
            if ai.get("overall_summary"):
                print(f"Summary: {ai.get('overall_summary')}")

            ai_findings = ai.get("findings", [])
            if ai_findings:
                print(f"\nAI Identified Issues ({len(ai_findings)}):")
                for j, item in enumerate(ai_findings, 1):
                    sev = format_severity(item.get("severity", "MEDIUM"))
                    line_str = f"Line {item.get('line_number')}: " if item.get("line_number") else ""
                    print(f"  {j}. {sev} {line_str}{COLOR_BOLD}{item.get('issue')}{COLOR_RESET}")
                    print(f"     {item.get('explanation')}")
                    if item.get("suggested_fix"):
                        print(f"     Fix: {COLOR_GREEN}{item.get('suggested_fix')}{COLOR_RESET}")

            if ai.get("refactored_code"):
                print(f"\n{COLOR_BOLD}Suggested Refactoring:{COLOR_RESET}\n{ai.get('refactored_code')}\n")

    print()
    return 0 if record.summary.errors == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI-Powered Bug Detection System - Static AST & AI Review CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="Path to Python file to analyze (use '-' to read from stdin)",
    )
    parser.add_argument(
        "--ai",
        action="store_true",
        help="Perform optional AI review using OpenAI API (reads OPENAI_API_KEY from .env)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not save this review to the SQLite history database",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON analysis record",
    )
    parser.add_argument(
        "--history",
        action="store_true",
        help="List recent review history",
    )
    parser.add_argument(
        "--history-limit",
        type=int,
        default=10,
        help="Number of history items to show (default: 10)",
    )
    parser.add_argument(
        "--clear-history",
        action="store_true",
        help="Clear all reviews from SQLite database",
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="Custom SQLite database file path",
    )

    args = parser.parse_args()
    sys.exit(run_cli(args))


if __name__ == "__main__":
    main()
