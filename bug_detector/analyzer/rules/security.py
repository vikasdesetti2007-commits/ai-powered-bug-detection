"""Security static analysis rules (AST-based)."""

import ast
from bug_detector.analyzer.rules.base import BaseRule
from bug_detector.models import FindingCategory, Severity


class EvalExecRule(BaseRule):
    """SEC001: Detects dangerous execution via eval() or exec()."""
    rule_id = "SEC001"
    name = "Dangerous Dynamic Code Execution"
    category = FindingCategory.SECURITY
    severity = Severity.ERROR
    description = "Use of eval() or exec() can allow arbitrary code execution vulnerabilities."

    def visit_Call(self, node: ast.Call) -> None:
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id in ("builtins", "__builtins__"):
                func_name = node.func.attr

        if func_name in ("eval", "exec"):
            suggestion = (
                "Avoid eval() and exec(). Use ast.literal_eval() for safe literal parsing, "
                "or refactor to structured data dispatching."
            )
            self.add_finding(
                node,
                message=f"Dangerous dynamic code execution detected: call to '{func_name}()'.",
                suggestion=suggestion,
            )

        self.generic_visit(node)


class UnsafeSubprocessRule(BaseRule):
    """SEC002: Detects os.system() or subprocess with shell=True."""
    rule_id = "SEC002"
    name = "Unsafe Command Execution"
    category = FindingCategory.SECURITY
    severity = Severity.ERROR
    description = "Executing shell commands directly or with shell=True exposes the application to command injection."

    def visit_Call(self, node: ast.Call) -> None:
        # Check os.system(...)
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                if node.func.attr == "system":
                    self.add_finding(
                        node,
                        message="Call to 'os.system()' is vulnerable to command injection.",
                        suggestion="Replace 'os.system()' with 'subprocess.run(args, check=True)' with a sequence of arguments and shell=False.",
                    )

            # Check subprocess.*(..., shell=True)
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
                if node.func.attr in ("run", "call", "check_call", "check_output", "Popen"):
                    for kw in node.keywords:
                        if kw.arg == "shell":
                            if isinstance(kw.value, ast.Constant) and kw.value.value is True:
                                self.add_finding(
                                    node,
                                    message=f"Subprocess call '{node.func.attr}()' invoked with shell=True.",
                                    suggestion="Pass arguments as a list (e.g. ['cmd', 'arg']) and set shell=False to prevent command injection.",
                                )

        self.generic_visit(node)


class InsecureTempfileRule(BaseRule):
    """SEC003: Detects use of insecure tempfile.mktemp()."""
    rule_id = "SEC003"
    name = "Insecure Temporary File Creation"
    category = FindingCategory.SECURITY
    severity = Severity.WARNING
    description = "tempfile.mktemp() is deprecated and vulnerable to symlink / race condition attacks."

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "tempfile":
                if node.func.attr == "mktemp":
                    self.add_finding(
                        node,
                        message="Use of deprecated and insecure 'tempfile.mktemp()'.",
                        suggestion="Use 'tempfile.NamedTemporaryFile()' or 'tempfile.TemporaryDirectory()' instead.",
                    )

        self.generic_visit(node)
