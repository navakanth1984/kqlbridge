"""
ir/validator.py — KQLBridge Semantic IR Validator
==================================================
Phase 2A foundation. Phase 2B/3A additions.

12 validation rules:
    V001  EMPTY_SOURCE_TABLE    — source_table is None or blank           ERROR
    V002  DUPLICATE_SYMBOL_ID   — same symbol_id registered twice         ERROR
    V003  MISSING_ALIAS         — ProjectionItem/AggregateItem no alias   ERROR
    V004  NULL_PREDICATE        — SemanticFilter.predicate is None        ERROR
    V005  BROKEN_LINEAGE        — derived_from refs a non-existent id     WARNING
    V006  UNKNOWN_AGG_FUNCTION  — function_name not in known set          WARNING
    V007  ORPHAN_SYMBOL_ID      — symbol_id absent from SymbolTable       ERROR
    V008  INVALID_CTE           — a CTE value is not a SemanticQuery      ERROR
    V009  EMPTY_UNION_INPUTS    — SemanticUnion has < 2 branches          ERROR
    V010  UNION_MAPPING_ORPHAN  — UnionColumnMapping symbol_id missing    WARNING
    V011  JOIN_CONDITION_EMPTY  — SemanticJoin has no conditions          ERROR
    V012  JOIN_CONDITION_ORPHAN — JoinCondition right_symbol_id missing   WARNING
    V013  DUPLICATE_ALIAS       — Two ProjectionItems share the same alias ERROR

Usage::

    # Auto-raise during development:
    ir = to_semantic_ir(parse("T | where x == 1"), validate=True)

    # Explicit structured diagnostics:
    result = validate_ir(ir)
    assert result.is_valid, result.summary()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Set


# ─── IRValidationError ───────────────────────────────────────────────────────

class IRValidationError(Exception):
    """
    Raised by to_semantic_ir(validate=True) when ERROR-severity violations
    are found in the generated IR.

    Attributes:
        result: The full ValidationResult for programmatic inspection.

    Example::

        try:
            ir = to_semantic_ir(parse("T | where x == 1"), validate=True)
        except IRValidationError as e:
            for issue in e.result.errors:
                print(issue)
    """
    def __init__(self, result: "ValidationResult") -> None:
        self.result = result
        super().__init__(result.summary())


# ─── Known aggregate function names ─────────────────────────────────────────

_KNOWN_AGG_FUNCTIONS: Set[str] = {
    "count", "sum", "avg", "min", "max", "dcount",
    "countif", "sumif", "avgif", "maxif", "minif", "dcountif",
    "percentile", "make_list", "stdev",
}


# ─── Issue and Result dataclasses ────────────────────────────────────────────

@dataclass
class ValidationIssue:
    """A single structural violation found during IR validation."""
    code: str
    severity: str      # "ERROR" | "WARNING"
    location: str
    message: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.severity} @ {self.location}: {self.message}"


@dataclass
class ValidationResult:
    """Aggregate result of an IR validation pass."""
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not any(i.severity == "ERROR" for i in self.issues)

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == "ERROR"]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == "WARNING"]

    def summary(self) -> str:
        if not self.issues:
            return "IR validation passed — no issues found."
        lines = [f"IR validation found {len(self.errors)} error(s), "
                 f"{len(self.warnings)} warning(s):"]
        for issue in self.issues:
            lines.append(f"  {issue}")
        return "\n".join(lines)


# ─── Public API ──────────────────────────────────────────────────────────────

def validate_ir(query: "SemanticQuery") -> ValidationResult:
    """
    Walk a SemanticQuery tree and check structural + lineage contracts.

    Args:
        query: A SemanticQuery produced by to_semantic_ir().

    Returns:
        ValidationResult — is_valid=True means no ERROR-severity issues.
    """
    # Import here to avoid circular imports at module load time
    from .nodes import (
        SemanticQuery, SemanticFilter, SemanticProjection, SemanticAggregate, SemanticJoin, SemanticUnion,
    )

    issues: List[ValidationIssue] = []

    # ── V001: source_table must be non-empty ──────────────────────────────
    if not query.source_table or not query.source_table.strip():
        issues.append(ValidationIssue(
            code="V001",
            severity="ERROR",
            location="SemanticQuery.source_table",
            message="source_table is None or blank — every query must name a source",
        ))

    # ── V002: no duplicate symbol_ids in SymbolTable ──────────────────────
    seen_ids: Set[int] = set()
    if query.symbol_table:
        for sym in query.symbol_table.all_symbols():
            if sym.id in seen_ids:
                issues.append(ValidationIssue(
                    code="V002",
                    severity="ERROR",
                    location=f"SymbolTable.symbol_id={sym.id}",
                    message=f"Duplicate symbol_id {sym.id} registered in SymbolTable",
                ))
            seen_ids.add(sym.id)

    # ── V003: ProjectionItem / AggregateItem alias must be non-empty ──────
    for i, step in enumerate(query.steps):
        if isinstance(step, SemanticProjection):
            for j, item in enumerate(step.items):
                if not item.alias or not item.alias.strip():
                    issues.append(ValidationIssue(
                        code="V003",
                        severity="ERROR",
                        location=f"steps[{i}]:SemanticProjection.items[{j}]",
                        message="ProjectionItem.alias is empty or blank",
                    ))
        if isinstance(step, SemanticAggregate):
            for j, item in enumerate(step.aggregations):
                if not item.alias or not item.alias.strip():
                    issues.append(ValidationIssue(
                        code="V003",
                        severity="ERROR",
                        location=f"steps[{i}]:SemanticAggregate.aggregations[{j}]",
                        message="AggregateItem.alias is empty or blank",
                    ))

    # ── V004: SemanticFilter.predicate must not be None ───────────────────
    for i, step in enumerate(query.steps):
        if isinstance(step, SemanticFilter):
            if step.predicate is None:
                issues.append(ValidationIssue(
                    code="V004",
                    severity="ERROR",
                    location=f"steps[{i}]:SemanticFilter",
                    message="SemanticFilter.predicate is None — filter has no condition",
                ))

    # ── V005: derived_from must reference existing symbol_ids ─────────────
    for i, step in enumerate(query.steps):
        if isinstance(step, SemanticProjection):
            for j, item in enumerate(step.items):
                for ref_id in item.derived_from:
                    if seen_ids and ref_id not in seen_ids:
                        issues.append(ValidationIssue(
                            code="V005",
                            severity="WARNING",
                            location=f"steps[{i}]:SemanticProjection.items[{j}].derived_from",
                            message=f"derived_from references symbol_id {ref_id} "
                                    f"which is not in the SymbolTable",
                        ))
        if isinstance(step, SemanticAggregate):
            for j, item in enumerate(step.aggregations):
                for ref_id in item.derived_from:
                    if seen_ids and ref_id not in seen_ids:
                        issues.append(ValidationIssue(
                            code="V005",
                            severity="WARNING",
                            location=f"steps[{i}]:SemanticAggregate.aggregations[{j}].derived_from",
                            message=f"derived_from references symbol_id {ref_id} "
                                    f"which is not in the SymbolTable",
                        ))

    # ── V006: AggregateItem.function_name should be known ─────────────────
    for i, step in enumerate(query.steps):
        if isinstance(step, SemanticAggregate):
            for j, item in enumerate(step.aggregations):
                if item.function_name not in _KNOWN_AGG_FUNCTIONS:
                    issues.append(ValidationIssue(
                        code="V006",
                        severity="WARNING",
                        location=f"steps[{i}]:SemanticAggregate.aggregations[{j}]",
                        message=f"Unknown aggregate function: {item.function_name!r}. "
                                f"Known: {sorted(_KNOWN_AGG_FUNCTIONS)}",
                    ))

    # ── V007: ProjectionItem/AggregateItem symbol_id in SymbolTable ───────
    for i, step in enumerate(query.steps):
        if isinstance(step, SemanticProjection):
            for j, item in enumerate(step.items):
                if item.symbol_id != 0 and seen_ids and item.symbol_id not in seen_ids:
                    issues.append(ValidationIssue(
                        code="V007",
                        severity="ERROR",
                        location=f"steps[{i}]:SemanticProjection.items[{j}]",
                        message=f"ProjectionItem.symbol_id {item.symbol_id} "
                                f"not found in SymbolTable",
                    ))
        if isinstance(step, SemanticAggregate):
            for j, item in enumerate(step.aggregations):
                if item.symbol_id != 0 and seen_ids and item.symbol_id not in seen_ids:
                    issues.append(ValidationIssue(
                        code="V007",
                        severity="ERROR",
                        location=f"steps[{i}]:SemanticAggregate.aggregations[{j}]",
                        message=f"AggregateItem.symbol_id {item.symbol_id} "
                                f"not found in SymbolTable",
                    ))

    # ── V008: CTE values must be SemanticQuery instances ──────────────────
    for cte_name, cte_val in query.ctes.items():
        if not isinstance(cte_val, SemanticQuery):
            issues.append(ValidationIssue(
                code="V008",
                severity="ERROR",
                location=f"ctes[{cte_name!r}]",
                message=f"CTE value for {cte_name!r} is {type(cte_val).__name__}, "
                        f"expected SemanticQuery",
            ))

    # ── V009: SemanticUnion must have >= 1 input branch (>= 2 total) ──────
    for i, step in enumerate(query.steps):
        if isinstance(step, SemanticUnion):
            if len(step.inputs) < 1:
                issues.append(ValidationIssue(
                    code="V009",
                    severity="ERROR",
                    location=f"steps[{i}]:SemanticUnion",
                    message=(
                        f"SemanticUnion requires >= 1 input branch, "
                        f"found {len(step.inputs)}"
                    ),
                ))

    # ── V010: UnionColumnMapping source symbol_ids must be in SymbolTable ──
    for i, step in enumerate(query.steps):
        if isinstance(step, SemanticUnion):
            for j, mapping in enumerate(step.mappings):
                for branch_idx, source_symbol_id in mapping.source_mappings.items():
                    if (
                        source_symbol_id is not None
                        and source_symbol_id != 0
                        and seen_ids
                        and source_symbol_id not in seen_ids
                    ):
                        issues.append(ValidationIssue(
                            code="V010",
                            severity="WARNING",
                            location=f"steps[{i}]:SemanticUnion.mappings[{j}].source_mappings[{branch_idx}]",
                            message=(
                                f"UnionColumnMapping source symbol_id "
                                f"{source_symbol_id} not in SymbolTable"
                            ),
                        ))

    # ── V011: SemanticJoin must have >= 1 condition ───────────────────────
    for i, step in enumerate(query.steps):
        if isinstance(step, SemanticJoin):
            if not step.conditions:
                issues.append(ValidationIssue(
                    code="V011",
                    severity="ERROR",
                    location=f"steps[{i}]:SemanticJoin",
                    message=(
                        "SemanticJoin.conditions is empty — at least one "
                        "join condition is required"
                    ),
                ))

    # ── V012: SemanticJoinCondition right_symbol_id in right SymbolTable ──
    for i, step in enumerate(query.steps):
        if isinstance(step, SemanticJoin):
            right_ids: Set[int] = set()
            if step.right_query.symbol_table:
                right_ids = {
                    s.id for s in step.right_query.symbol_table.all_symbols()
                }
            for j, cond in enumerate(step.conditions):
                if (
                    cond.right_symbol_id != 0
                    and right_ids
                    and cond.right_symbol_id not in right_ids
                ):
                    issues.append(ValidationIssue(
                        code="V012",
                        severity="WARNING",
                        location=f"steps[{i}]:SemanticJoin.conditions[{j}]",
                        message=(
                            f"SemanticJoinCondition right_symbol_id "
                            f"{cond.right_symbol_id} not in right "
                            f"SemanticQuery.symbol_table"
                        ),
                    ))

    # ── V013: No duplicate aliases within Projection or Aggregate scope ──
    # Scope: SemanticProjection.items  +  SemanticAggregate.aggregations
    # Duplicate aliases produce ambiguous SQL: SELECT a AS score, b AS score
    # or: SELECT COUNT(*) AS total, SUM(x) AS total FROM T GROUP BY region
    for i, step in enumerate(query.steps):
        if isinstance(step, SemanticProjection):
            seen_aliases: Set[str] = set()
            for j, item in enumerate(step.items):
                if item.alias and item.alias in seen_aliases:
                    issues.append(ValidationIssue(
                        code="V013",
                        severity="ERROR",
                        location=f"steps[{i}]:SemanticProjection.items[{j}]",
                        message=(
                            f"Duplicate alias {item.alias!r} in SemanticProjection "
                            f"— emitters produce ambiguous SQL "
                            f"(SELECT x AS {item.alias}, y AS {item.alias})"
                        ),
                    ))
                if item.alias:
                    seen_aliases.add(item.alias)

        if isinstance(step, SemanticAggregate):
            seen_agg_aliases: Set[str] = set()
            # Check aggregations namespace only (group_by aliases are typically
            # column names and are validated separately via symbol integrity)
            for j, item in enumerate(step.aggregations):
                if item.alias and item.alias in seen_agg_aliases:
                    issues.append(ValidationIssue(
                        code="V013",
                        severity="ERROR",
                        location=f"steps[{i}]:SemanticAggregate.aggregations[{j}]",
                        message=(
                            f"Duplicate alias {item.alias!r} in SemanticAggregate "
                            f"— two aggregation outputs share the same name "
                            f"(e.g. total = count(), total = sum(x))"
                        ),
                    ))
                if item.alias:
                    seen_agg_aliases.add(item.alias)

    return ValidationResult(issues=issues)
