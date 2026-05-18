"""
kqlbridge — KQL to Spark SQL / T-SQL transpiler
================================================
Public API:

    translate(kql, target="spark") → str
    detect_operators(kql) → list[str]
    is_supported(kql) → bool
    check(kql) → SemanticResult
"""

from __future__ import annotations
from typing import Literal

from .parser import parse
from lark.exceptions import UnexpectedInput as _LarkUnexpectedInput
from .semantic import check as _semantic_check, SemanticResult
from .lint import lint, LintResult  # noqa: F401 — public API
from .explain import explain, ExplainResult  # noqa: F401 — public API
from .generators.spark_sql import SparkSQLGenerator
from .generators.tsql import TSQLGenerator

__version__ = "0.1.0"
__all__ = ["translate", "detect_operators", "is_supported", "check", "__version__"]

_SPARK_GEN = SparkSQLGenerator()
_TSQL_GEN = TSQLGenerator()


def translate(
    kql: str,
    target: Literal["spark", "tsql"] = "spark",
) -> str:
    """
    Translate a KQL query string to the target SQL dialect.

    Args:
        kql:    KQL query string
        target: "spark" (default) or "tsql"

    Returns:
        SQL string in the target dialect

    Raises:
        lark.exceptions.UnexpectedInput: on KQL parse error
        NotImplementedError: if target generator is not implemented
        ValueError: if query contains unsupported operators (check first)
    """
    try:
        query = parse(kql)
    except _LarkUnexpectedInput as e:
        raise ValueError(
            "Unsupported KQL syntax — contains operators or constructs not supported "
            "in this version. Use is_supported() to check before translating.\n"
            f"Detail: {e}"
        ) from None
    if target == "spark":
        return _SPARK_GEN.generate(query)
    if target == "tsql":
        return _TSQL_GEN.generate(query)
    raise ValueError(f"Unknown target: {target!r}. Use 'spark' or 'tsql'.")


def detect_operators(kql: str) -> list[str]:
    """
    Return the list of KQL operators used in a query string.

    Useful for routing agents that need to decide which engine to use.

    Example:
        detect_operators("T | where x == 1 | summarize count() by y")
        → ['where', 'summarize']
    """
    from .ast_nodes import (
        WhereOp, ProjectOp, SummarizeOp, OrderOp, TakeOp,
        DistinctOp, ExtendOp, JoinOp, UnionOp, CountOp,
    )
    _OP_NAMES = {
        WhereOp: "where",
        ProjectOp: "project",
        SummarizeOp: "summarize",
        OrderOp: "order by",
        TakeOp: "take",
        DistinctOp: "distinct",
        ExtendOp: "extend",
        JoinOp: "join",
        UnionOp: "union",
        CountOp: "count",
    }

    try:
        query = parse(kql)
        return [_OP_NAMES[type(op)] for op in query.pipes
                if type(op) in _OP_NAMES]
    except Exception:
        return []


def is_supported(kql: str) -> bool:
    """
    Return True if the query can be fully translated to Spark SQL.

    Queries with unsupported operators (make-series, render, etc.)
    return False — the caller should keep those in the native KQL engine.
    """
    try:
        query = parse(kql)
        result = _semantic_check(query)
        return result.is_supported
    except Exception:
        return False


def check(kql: str) -> SemanticResult:
    """
    Parse and semantically validate a KQL query.

    Returns a SemanticResult with:
    - is_valid: True if AST is structurally sound
    - is_supported: True if query can be fully translated
    - warnings: Non-blocking issues
    - errors: Blocking issues (unsupported operators, ambiguities)
    """
    query = parse(kql)
    return _semantic_check(query)
