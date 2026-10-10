"""Correctness static analysis rules (AST-based)."""

import ast
from typing import Any, List, Set, Union
from bug_detector.analyzer.rules.base import BaseRule
from bug_detector.models import FindingCategory, Severity


class MutableDefaultArgRule(BaseRule):
    """COR001: Detects mutable default arguments in function definitions."""
    rule_id = "COR001"
    name = "Mutable Default Argument"
    category = FindingCategory.CORRECTNESS
    severity = Severity.WARNING
    description = (
        "Default parameter values are evaluated once at function definition time. "
        "Mutable defaults (e.g. lists, dicts, sets) are shared across all calls."
    )

    def _is_mutable_node(self, node: ast.AST) -> bool:
        if isinstance(node, (ast.List, ast.Dict, ast.Set)):
            return True
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ("list", "dict", "set"):
                return True
        return False

    def _check_defaults(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> None:
        all_defaults = list(node.args.defaults) + [d for d in node.args.kw_defaults if d is not None]
        for default_expr in all_defaults:
            if self._is_mutable_node(default_expr):
                self.add_finding(
                    default_expr,
                    message=f"Function '{node.name}' uses a mutable default argument.",
                    suggestion="Replace mutable default with 'None' and initialize inside the function (e.g. 'if arg is None: arg = []').",
                )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_defaults(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_defaults(node)
        self.generic_visit(node)


class IdentityComparisonRule(BaseRule):
    """COR002: Detects comparison to None/booleans using == or != instead of 'is' or truthiness."""
    rule_id = "COR002"
    name = "Ineffective Identity Comparison"
    category = FindingCategory.CORRECTNESS
    severity = Severity.WARNING
    description = "Comparisons to None should use 'is' or 'is not'. Comparisons to True/False should use truthiness."

    def visit_Compare(self, node: ast.Compare) -> None:
        for op, comparator in zip(node.ops, node.comparators):
            # Check left vs comparator
            for term in (node.left, comparator):
                if isinstance(term, ast.Constant):
                    if term.value is None and isinstance(op, (ast.Eq, ast.NotEq)):
                        op_str = "==" if isinstance(op, ast.Eq) else "!="
                        rec = "is None" if isinstance(op, ast.Eq) else "is not None"
                        self.add_finding(
                            node,
                            message=f"Comparison with None using '{op_str}' operator.",
                            suggestion=f"Use '{rec}' instead of '{op_str} None'.",
                        )
                        break
                    elif isinstance(term.value, bool) and isinstance(op, (ast.Eq, ast.NotEq, ast.Is, ast.IsNot)):
                        self.add_finding(
                            node,
                            message=f"Comparison with boolean literal '{term.value}'.",
                            suggestion="Simplify condition to 'if x:' or 'if not x:' instead of comparing to boolean literals.",
                        )
                        break

        self.generic_visit(node)


class DivisionByZeroRule(BaseRule):
    """COR003: Detects literal division or modulo by zero."""
    rule_id = "COR003"
    name = "Division by Zero"
    category = FindingCategory.CORRECTNESS
    severity = Severity.ERROR
    description = "Division or modulo by literal zero always raises a ZeroDivisionError."

    def visit_BinOp(self, node: ast.BinOp) -> None:
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            if isinstance(node.right, ast.Constant) and node.right.value in (0, 0.0):
                op_name = "/" if isinstance(node.op, ast.Div) else ("//" if isinstance(node.op, ast.FloorDiv) else "%")
                self.add_finding(
                    node,
                    message=f"Zero division detected: operation using divisor '{node.right.value}' with operator '{op_name}'.",
                    suggestion="Ensure the divisor is non-zero or add a safeguard check before division.",
                )
        self.generic_visit(node)


class DuplicateDictKeysRule(BaseRule):
    """COR004: Detects duplicate literal keys in dictionary definitions."""
    rule_id = "COR004"
    name = "Duplicate Dictionary Key"
    category = FindingCategory.CORRECTNESS
    severity = Severity.WARNING
    description = "Duplicate keys in a dictionary literal overwrite previous keys silently."

    def visit_Dict(self, node: ast.Dict) -> None:
        seen_keys: Set[Any] = set()
        for key_node in node.keys:
            if key_node is not None and isinstance(key_node, ast.Constant):
                val = key_node.value
                # Keys like (1, True) or ("a", "a")
                key_repr = (type(val), val)
                if key_repr in seen_keys:
                    self.add_finding(
                        key_node,
                        message=f"Duplicate key '{val}' in dictionary literal.",
                        suggestion="Remove the duplicate key or verify if a distinct key name was intended.",
                    )
                else:
                    seen_keys.add(key_repr)

        self.generic_visit(node)


class UnreachableCodeRule(BaseRule):
    """COR005: Detects unreachable statements after return, raise, break, or continue."""
    rule_id = "COR005"
    name = "Unreachable Code"
    category = FindingCategory.CORRECTNESS
    severity = Severity.WARNING
    description = "Statements immediately following return, raise, break, or continue in the same block are never executed."

    def _check_block(self, body: List[ast.stmt]) -> None:
        terminated = False
        terminator_stmt: Optional[ast.stmt] = None

        for stmt in body:
            if terminated and terminator_stmt:
                self.add_finding(
                    stmt,
                    message=f"Unreachable statement detected following '{terminator_stmt.__class__.__name__.lower()}' at line {terminator_stmt.lineno}.",
                    suggestion="Remove or relocate unreachable statements.",
                )
                # Flag only the first unreachable statement in sequence to avoid noise
                break

            if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                terminated = True
                terminator_stmt = stmt

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_block(node.body)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_block(node.body)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._check_block(node.body)
        self._check_block(node.orelse)
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self._check_block(node.body)
        self._check_block(node.orelse)
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        self._check_block(node.body)
        self._check_block(node.orelse)
        self.generic_visit(node)
