"""Rule registry and default rule loader for static analysis."""

from typing import List, Type
from bug_detector.analyzer.rules.base import BaseRule
from bug_detector.analyzer.rules.security import (
    EvalExecRule,
    UnsafeSubprocessRule,
    InsecureTempfileRule,
)
from bug_detector.analyzer.rules.correctness import (
    MutableDefaultArgRule,
    IdentityComparisonRule,
    DivisionByZeroRule,
    DuplicateDictKeysRule,
    UnreachableCodeRule,
)
from bug_detector.analyzer.rules.style import (
    BareExceptRule,
    ShadowedBuiltinsRule,
    AssertTupleRule,
)

ALL_RULES: List[Type[BaseRule]] = [
    # Security
    EvalExecRule,
    UnsafeSubprocessRule,
    InsecureTempfileRule,
    # Correctness
    MutableDefaultArgRule,
    IdentityComparisonRule,
    DivisionByZeroRule,
    DuplicateDictKeysRule,
    UnreachableCodeRule,
    # Style
    BareExceptRule,
    ShadowedBuiltinsRule,
    AssertTupleRule,
]

__all__ = [
    "BaseRule",
    "EvalExecRule",
    "UnsafeSubprocessRule",
    "InsecureTempfileRule",
    "MutableDefaultArgRule",
    "IdentityComparisonRule",
    "DivisionByZeroRule",
    "DuplicateDictKeysRule",
    "UnreachableCodeRule",
    "BareExceptRule",
    "ShadowedBuiltinsRule",
    "AssertTupleRule",
    "ALL_RULES",
]
