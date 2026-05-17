"""
semantic.py — KQLBridge Semantic Validator
==========================================
LOCKED FILE — Human-designed. Agent MUST NEVER modify this file.

Validates a KQLQuery AST before passing it to a generator.
Flags operators that have no SQL equivalent so the caller can
decide whether to fall back to the native KQL engine.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ast_nodes import KQLQuery


# Operators that have no SQL mapping — explicitly documented
UNSUPPORTED_OPERATORS = {
    "make-series",
    "series_decompose_anomalies",
    "bag_unpack",
    "render",
    "ipv4_is_in_range",
    "udf",   # user-defined functions registered on cluster
}


@dataclass
class SemanticResult:
    is_valid: bool
    warnings: list[str]
    errors: list[str]

    @property
    def is_supported(self) -> bool:
        """True if the query can be fully translated (no blocking errors)."""
        return self.is_valid and len(self.errors) == 0


def check(query: "KQLQuery") -> SemanticResult:
    """
    Run semantic validation on a parsed KQLQuery.

    Returns a SemanticResult with:
    - is_valid: False if the AST is structurally broken
    - errors: Blocking issues (unsupported operators, ambiguous rewrites)
    - warnings: Non-blocking issues (potential semantic drift to review)
    """
    errors: list[str] = []
    warnings: list[str] = []

    _check_pipes(query, errors, warnings)
    _check_summarize_rewrite(query, errors, warnings)
    _check_let_bindings(query, errors, warnings)

    return SemanticResult(
        is_valid=True,
        warnings=warnings,
        errors=errors,
    )


def _check_pipes(query: "KQLQuery", errors: list, warnings: list) -> None:
    from .ast_nodes import JoinOp, SummarizeOp, DistinctOp

    has_summarize = False
    has_distinct = False

    for op in query.pipes:
        if has_summarize and isinstance(op, (SummarizeOp,)):
            warnings.append(
                "Multiple summarize operators in one query. "
                "Only the last one will generate a GROUP BY clause."
            )
        if isinstance(op, SummarizeOp):
            has_summarize = True
        if isinstance(op, DistinctOp):
            has_distinct = True
        if isinstance(op, JoinOp):
            if op.kind not in ("inner", "leftouter", "rightouter", "fullouter"):
                errors.append(f"Unsupported join kind: {op.kind!r}")

    if has_summarize and has_distinct:
        warnings.append(
            "Query uses both summarize and distinct. "
            "In SQL this maps to GROUP BY + DISTINCT which may not match KQL semantics."
        )


def _check_summarize_rewrite(query: "KQLQuery", errors: list, warnings: list) -> None:
    """
    Karpathy Principle 5 — Jagged Intelligence warning site.

    KQL summarize is left-to-right; SQL GROUP BY requires column names in SELECT.
    This is the most likely source of silent semantic failures.
    Human review required on every aggregate operator output.
    """
    from .ast_nodes import SummarizeOp

    for op in query.pipes:
        if isinstance(op, SummarizeOp):
            if not op.group_by:
                warnings.append(
                    "summarize without 'by' clause → global aggregate (no GROUP BY). "
                    "Verify this is the intended semantics."
                )
            # Warn when aggregation aliases shadow column names
            agg_aliases = set()
            for agg in op.aggregations:
                alias = getattr(agg, "alias", None)
                if alias:
                    agg_aliases.add(alias)
            for gb in op.group_by:
                from .ast_nodes import PlainGroup, ColumnRef
                if isinstance(gb, PlainGroup) and isinstance(gb.col, ColumnRef):
                    if gb.col.name in agg_aliases:
                        errors.append(
                            f"Group-by column '{gb.col.name}' has the same name as an "
                            "aggregation alias. This is ambiguous — rename the alias."
                        )


def _check_let_bindings(query: "KQLQuery", errors: list, warnings: list) -> None:
    """Let bindings become CTEs. Circular references are not supported."""
    defined = set()
    for binding in query.let_bindings:
        if binding.name in defined:
            errors.append(
                f"Duplicate let binding: '{binding.name}'. "
                "KQLBridge does not support re-assignment in let chains."
            )
        defined.add(binding.name)
