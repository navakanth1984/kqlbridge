"""
lint.py — KQLBridge Semantic Drift Detector
============================================
AGENT MODIFIABLE — add new lint rules here following the LintRule pattern.

Each rule is a function: (KQLQuery) -> list[LintIssue]
Rules detect cases where the translation is syntactically correct
but semantically different from the KQL intent.

v0.3 rules:
  LINT-01  Case-insensitive operator =~ silently becomes case-sensitive =
  LINT-02  has operator loses word-boundary semantics (becomes LIKE '%x%')
  LINT-03  bin(ts, 7d) is epoch-relative, not calendar weeks
  LINT-04  let binding chain — forward references not guaranteed
  LINT-05  extend self-reference (col = col) — ambiguous in Spark SQL
  LINT-06  distinct * after project — redundant, returns same as project
"""

from __future__ import annotations
from dataclasses import dataclass, field

from .ast_nodes import (
    KQLQuery, WhereOp, ExtendOp, DistinctOp, ProjectOp,
    Comparison, StringOp, BinGroup,
)


# ─── Result types ────────────────────────────────────────────────────────────

@dataclass
class LintIssue:
    rule_id: str
    severity: str          # "HIGH" | "MEDIUM" | "LOW"
    operator: str          # which KQL operator triggered this
    kql_intent: str        # what KQL means
    sql_behaviour: str     # what the translated SQL actually does
    fix: str               # recommended remediation


@dataclass
class LintResult:
    issues: list[LintIssue] = field(default_factory=list)

    @property
    def risk(self) -> str:
        if any(i.severity == "HIGH" for i in self.issues):
            return "HIGH"
        if any(i.severity == "MEDIUM" for i in self.issues):
            return "MEDIUM"
        return "LOW" if self.issues else "CLEAN"

    @property
    def is_clean(self) -> bool:
        return len(self.issues) == 0


# ─── Rule implementations ────────────────────────────────────────────────────

def _rule_lint01_case_insensitive_op(query: KQLQuery) -> list[LintIssue]:
    """LINT-01: =~ operator is case-insensitive in KQL, becomes = in SQL."""
    issues = []
    for op in query.pipes:
        if isinstance(op, WhereOp):
            _walk_comparison(op.condition, issues)
    return issues


def _walk_comparison(node, issues: list[LintIssue]) -> None:
    from .ast_nodes import LogicalOp, Negation
    if isinstance(node, Comparison):
        if node.op == "=~":
            issues.append(LintIssue(
                rule_id="LINT-01",
                severity="HIGH",
                operator="where",
                kql_intent="=~ is case-insensitive: matches 'Error', 'ERROR', 'error'",
                sql_behaviour="= is case-sensitive in Spark SQL: only matches exact case",
                fix="Wrap both sides with LOWER(): WHERE LOWER(col) = LOWER('value')",
            ))
    elif isinstance(node, LogicalOp):
        _walk_comparison(node.left, issues)
        _walk_comparison(node.right, issues)
    elif isinstance(node, Negation):
        _walk_comparison(node.expr, issues)


def _rule_lint02_has_word_boundary(query: KQLQuery) -> list[LintIssue]:
    """LINT-02: has is word-boundary aware in KQL, LIKE '%x%' is not."""
    issues = []
    for op in query.pipes:
        if isinstance(op, WhereOp):
            _walk_string_op(op.condition, issues)
    return issues


def _walk_string_op(node, issues: list[LintIssue]) -> None:
    from .ast_nodes import LogicalOp, Negation
    if isinstance(node, StringOp) and node.op == "has":
        issues.append(LintIssue(
            rule_id="LINT-02",
            severity="HIGH",
            operator="where ... has",
            kql_intent=f"has '{node.value}' matches whole words only (word-boundary aware)",
            sql_behaviour=f"LIKE '%{node.value}%' matches anywhere including partial words",
            fix=f"Use: WHERE col LIKE '% {node.value} %' OR col LIKE '{node.value} %' "
                f"OR col LIKE '% {node.value}' OR col = '{node.value}'",
        ))
    elif isinstance(node, LogicalOp):
        _walk_string_op(node.left, issues)
        _walk_string_op(node.right, issues)
    elif isinstance(node, Negation):
        _walk_string_op(node.expr, issues)


def _rule_lint03_bin_epoch_relative(query: KQLQuery) -> list[LintIssue]:
    """LINT-03: bin(ts, 7d) buckets from Unix epoch, not calendar weeks."""
    issues = []
    for op in query.pipes:
        from .ast_nodes import SummarizeOp
        if isinstance(op, SummarizeOp):
            for gb in op.group_by:
                if isinstance(gb, BinGroup):
                    if gb.unit == "d" and gb.amount >= 7:
                        issues.append(LintIssue(
                            rule_id="LINT-03",
                            severity="HIGH",
                            operator="summarize ... bin",
                            kql_intent=f"bin(col, {gb.amount}d) creates {gb.amount}-day buckets",
                            sql_behaviour=f"DATE_TRUNC buckets start from Unix epoch (Thu Jan 1 1970), "
                                         f"not calendar {('weeks' if gb.amount == 7 else f'{gb.amount}-day periods')}",
                            fix="Use bin(col, 1d) and aggregate weeks in your BI layer, "
                                "or use DATE_TRUNC('week', col) directly for calendar weeks",
                        ))
    return issues


def _rule_lint04_let_chain_order(query: KQLQuery) -> list[LintIssue]:
    """LINT-04: let bindings that reference earlier bindings may not resolve."""
    issues = []
    if len(query.let_bindings) < 2:
        return issues
    defined = set()
    for binding in query.let_bindings:
        # Check if this binding's table references a previously defined binding
        if binding.value.table in defined:
            pass  # this is fine — forward reference resolved
        defined.add(binding.name)
        # Check if the binding references a name not yet defined
        ref_table = binding.value.table
        if ref_table not in defined and ref_table != "__scalar__":
            # Might reference a real table — fine
            pass
    # Flag if any binding references a later binding (forward reference)
    names = [b.name for b in query.let_bindings]
    for i, binding in enumerate(query.let_bindings):
        ref = binding.value.table
        if ref in names and names.index(ref) > i:
            issues.append(LintIssue(
                rule_id="LINT-04",
                severity="MEDIUM",
                operator="let",
                kql_intent=f"let {binding.name} references '{ref}' which is defined later",
                sql_behaviour="CTEs in WITH clause must be defined before they are referenced",
                fix=f"Reorder let bindings so '{ref}' is defined before '{binding.name}'",
            ))
    return issues


def _rule_lint05_extend_self_reference(query: KQLQuery) -> list[LintIssue]:
    """LINT-05: extend col = col — self-assignment is ambiguous in Spark SQL."""
    issues = []
    for op in query.pipes:
        if isinstance(op, ExtendOp):
            from .ast_nodes import ColumnRef
            for name, expr in op.assignments:
                if isinstance(expr, ColumnRef) and expr.name == name:
                    issues.append(LintIssue(
                        rule_id="LINT-05",
                        severity="MEDIUM",
                        operator="extend",
                        kql_intent=f"extend {name} = {name} is a no-op in KQL",
                        sql_behaviour="SELECT *, col AS col may cause 'ambiguous column' error in Spark",
                        fix=f"Remove the self-referencing assignment: extend {name} = {name}",
                    ))
    return issues


def _rule_lint06_distinct_after_project(query: KQLQuery) -> list[LintIssue]:
    """LINT-06: distinct * after project returns same rows as project alone."""
    issues = []
    for i, op in enumerate(query.pipes):
        if isinstance(op, DistinctOp) and op.star:
            if i > 0 and isinstance(query.pipes[i - 1], ProjectOp):
                issues.append(LintIssue(
                    rule_id="LINT-06",
                    severity="LOW",
                    operator="distinct *",
                    kql_intent="distinct * deduplicates all columns",
                    sql_behaviour="After project, SELECT DISTINCT * is redundant if projected "
                                  "columns already form a unique key",
                    fix="Remove distinct * or apply distinct before project if deduplication is needed",
                ))
    return issues


# ─── Public API ──────────────────────────────────────────────────────────────

_RULES = [
    _rule_lint01_case_insensitive_op,
    _rule_lint02_has_word_boundary,
    _rule_lint03_bin_epoch_relative,
    _rule_lint04_let_chain_order,
    _rule_lint05_extend_self_reference,
    _rule_lint06_distinct_after_project,
]


def lint(kql: str) -> LintResult:
    """
    Run all semantic drift lint rules on a KQL query.

    Returns a LintResult with zero or more LintIssues.
    Does not raise on unsupported operators — returns empty result instead.
    """
    from .parser import parse
    from lark.exceptions import UnexpectedInput

    try:
        query = parse(kql)
    except (UnexpectedInput, NotImplementedError, ValueError):
        return LintResult()  # unparseable — lint can't help here

    issues = []
    for rule in _RULES:
        issues.extend(rule(query))

    return LintResult(issues=issues)
