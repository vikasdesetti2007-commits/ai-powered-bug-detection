"""Style and code quality static analysis rules (AST-based)."""

import ast
from typing import Set
from bug_detector.analyzer.rules.base import BaseRule
from bug_detector.models import FindingCategory, Severity

# Commonly shadowed built-in identifiers
COMMON_BUILTINS: Set[str] = {
    "list", "dict", "set", "str", "int", "float", "bool",
    "id", "type", "input", "filter", "map", "range", "len",
    "open", "format", "dir", "min", "max", "sum", "all", "any"
}


class BareExceptRule(BaseRule):
    """STY001: Detects bare except: or except BaseException: clauses."""
    rule_id = "STY001"
    name = "Bare or Overly Broad Exception Handler"
    category = FindingCategory.STYLE
    severity = Severity.WARNING
    description = (
        "A bare 'except:' or 'except BaseException:' catches SystemExit and KeyboardInterrupt, "
        "making programs harder to terminate or debug."
    )

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None:
            self.add_finding(
                node,
                message="Bare 'except:' clause catches all exceptions including system interrupts.",
                suggestion="Catch specific exception types or use 'except Exception:' at minimum.",
            )
        elif isinstance(node.type, ast.Name) and node.type.id == "BaseException":
            self.add_finding(
                node,
                message="Overly broad 'except BaseException:' clause catches system-exiting signals.",
                suggestion="Catch 'Exception' instead of 'BaseException' unless deliberately writing a top-level crash handler.",
            )
        self.generic_visit(node)


class ShadowedBuiltinsRule(BaseRule):
    """STY002: Detects local variables or parameters shadowing Python built-in names."""
    rule_id = "STY002"
    name = "Shadowed Built-in Identifier"
    category = FindingCategory.STYLE
    severity = Severity.INFO
    description = "Assigning to standard built-in names (e.g. list, id, str) masks standard library functions and causes subtle bugs."

    def _check_name(self, name: str, node: ast.AST, context_desc: str) -> None:
        if name in COMMON_BUILTINS:
            self.add_finding(
                node,
                message=f"{context_desc} '{name}' shadows a built-in Python function or type.",
                suggestion=f"Rename '{name}' to something more descriptive (e.g. '{name}_val', 'item_{name}').",
            )

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._check_name(target.id, target, "Variable assignment")
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name):
            self._check_name(node.target.id, node.target, "Annotated variable")
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        for arg in node.args.args + node.args.kwonlyargs:
            self._check_name(arg.arg, arg, f"Parameter in function '{node.name}'")
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        for arg in node.args.args + node.args.kwonlyargs:
            self._check_name(arg.arg, arg, f"Parameter in async function '{node.name}'")
        self.generic_visit(node)


class AssertTupleRule(BaseRule):
    """STY003: Detects assertions testing a 2-tuple, which always evaluates to True."""
    rule_id = "STY003"
    name = "Asserting a Tuple Literal"
    category = FindingCategory.STYLE
    severity = Severity.ERROR
    description = "assert (condition, message) evaluates as a non-empty tuple, which is always True in Python."

    def visit_Assert(self, node: ast.Assert) -> None:
        if isinstance(node.test, ast.Tuple) and len(node.test.elts) > 0:
            self.add_finding(
                node,
                message="Assertion on non-empty tuple always evaluates to True, even if the condition fails.",
                suggestion="Use 'assert condition, message' without parentheses around the whole assertion.",
            )
        self.generic_visit(node)
