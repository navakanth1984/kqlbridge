"""
explain.py — KQLBridge Translation Annotator
=============================================
AGENT MODIFIABLE — add new annotations here following the _Annotation pattern.

Produces annotated SQL with inline comments explaining every semantic
decision made during KQL → SQL translation. Designed for:

  - MCT training: students see exactly WHY the SQL looks the way it does
  - Enterprise review: migration teams validate translation intent
  - Debugging: identify where translation diverges from expectation

Usage:
    from kqlbridge.explain import explain
    result = explain("AppLogs | where Level == 'Error' | take 10")
    print(result.annotated_sql)
    print(result.summary)
"""

from __future__ import annotations
from dataclasses import dataclass, field

from .ast_nodes import (
    KQLQuery, WhereOp, ProjectOp, SummarizeOp, OrderOp, TakeOp,
    DistinctOp, ExtendOp, JoinOp, UnionOp, CountOp,
    AgoExpr, BinGroup, Comparison, StringOp, InExpr, LogicalOp,
    IffExpr, SubqueryInExpr,
)


# ─── Result types ────────────────────────────────────────────────────────────

@dataclass
class ExplainResult:
    kql: str
    sql: str
    annotated_sql: str
    annotations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        lines = ["KQL → SQL Translation Summary"]
        lines.append("=" * 45)
        lines.append(f"Operators translated: {len(self.annotations)}")
        if self.warnings:
            lines.append(f"Semantic warnings   : {len(self.warnings)}")
        lines.append("")
        for i, note in enumerate(self.annotations, 1):
            lines.append(f"  {i:2}. {note}")
        if self.warnings:
            lines.append("")
            lines.append("Semantic drift warnings:")
            for w in self.warnings:
                lines.append(f"  ⚠  {w}")
        return "\n".join(lines)


# ─── Annotation rules ────────────────────────────────────────────────────────

def _annotate_query(query: KQLQuery) -> tuple[list[str], list[str]]:
    """Walk the AST and collect annotations + semantic warnings."""
    notes = []
    warnings = []

    # let bindings → CTEs
    for binding in query.let_bindings:
        notes.append(
            f"let {binding.name} → WITH {binding.name} AS (...) "
            f"[KQL let becomes a SQL Common Table Expression]"
        )

    # pipe operators
    for op in query.pipes:
        _annotate_op(op, notes, warnings)

    return notes, warnings


def _annotate_op(op, notes: list[str], warnings: list[str]) -> None:
    if isinstance(op, WhereOp):
        _annotate_where(op, notes, warnings)

    elif isinstance(op, ProjectOp):
        aliases = op.aliases or {}
        if aliases:
            alias_list = ", ".join(f"{s} AS {a}" for s, a in aliases.items())
            notes.append(f"project col=alias → SELECT {alias_list} [column renaming]")
        else:
            notes.append(
                f"project {', '.join(op.columns[:3])}{'...' if len(op.columns) > 3 else ''} "
                f"→ SELECT specific columns [drops all others]"
            )

    elif isinstance(op, SummarizeOp):
        agg_names = []
        for agg in op.aggregations:
            agg_names.append(type(agg).__name__.replace("Agg", "").lower() + "()")
        gb_parts = []
        for gb in op.group_by:
            if isinstance(gb, BinGroup):
                gb_parts.append(f"bin({gb.amount}{gb.unit})")
                _annotate_bin(gb.amount, gb.unit, notes, warnings)
            else:
                gb_parts.append(str(gb.col) if hasattr(gb.col, '__str__') else "col")
        notes.append(
            f"summarize {', '.join(agg_names)} by {', '.join(gb_parts) or 'nothing'} "
            f"→ SELECT aggs FROM ... GROUP BY"
        )

    elif isinstance(op, OrderOp):
        items = [f"{it.direction.upper()}" for it in op.items]
        notes.append(
            f"order by → ORDER BY {', '.join(items)} "
            f"[KQL 'sort by' is identical — both map to ORDER BY]"
        )

    elif isinstance(op, TakeOp):
        notes.append(
            f"take {op.n} → LIMIT {op.n} (Spark) / TOP {op.n} (T-SQL) "
            f"[non-deterministic without order by]"
        )

    elif isinstance(op, DistinctOp):
        if op.star:
            notes.append("distinct * → SELECT DISTINCT * [deduplicates all columns]")
        else:
            notes.append(
                f"distinct {', '.join(op.columns)} → SELECT DISTINCT {', '.join(op.columns)}"
            )

    elif isinstance(op, ExtendOp):
        for alias, expr in op.assignments:
            expr_note = _expr_note(expr)
            notes.append(f"extend {alias} = {expr_note} → SELECT *, expr AS {alias}")
            if isinstance(expr, IffExpr):
                notes.append(
                    "  iff() → CASE WHEN ... THEN ... ELSE ... END "
                    "[KQL conditional maps to SQL CASE expression]"
                )

    elif isinstance(op, JoinOp):
        kind_map = {
            "inner": "INNER JOIN",
            "leftouter": "LEFT OUTER JOIN",
            "rightouter": "RIGHT OUTER JOIN",
            "fullouter": "FULL OUTER JOIN",
        }
        sql_join = kind_map.get(op.kind, "INNER JOIN")
        notes.append(
            f"join kind={op.kind} on {', '.join(op.keys)} → {sql_join} ON key = key "
            f"[KQL join always requires explicit key columns]"
        )

    elif isinstance(op, UnionOp):
        subqueries = op.subqueries or {}
        sub_count = len(subqueries)
        notes.append(
            f"union {', '.join(op.tables[:3])} → UNION ALL "
            f"[KQL union is always UNION ALL — no implicit deduplication"
            + (f"; {sub_count} inline subquer{'y' if sub_count == 1 else 'ies'} translated]"
               if sub_count else "]")
        )

    elif isinstance(op, CountOp):
        notes.append(
            "count → SELECT COUNT(*) AS count_ "
            "[trailing underscore avoids SQL reserved word collision]"
        )


def _annotate_where(op: WhereOp, notes: list[str], warnings: list[str]) -> None:
    _walk_condition(op.condition, notes, warnings)


def _walk_condition(node, notes: list[str], warnings: list[str]) -> None:
    if isinstance(node, Comparison):
        if node.op == "=~":
            warnings.append(
                "=~ is case-insensitive in KQL but translates to = (case-sensitive) in SQL. "
                "Use LOWER() on both sides for correct behaviour."
            )
            notes.append("where col =~ val → WHERE col = val [⚠ case-insensitive → case-sensitive]")
        elif node.op == "==":
            notes.append("where col == val → WHERE col = val [KQL == becomes SQL =]")
        else:
            notes.append(f"where col {node.op} val → WHERE clause")

    elif isinstance(node, StringOp):
        if node.op == "has":
            warnings.append(
                f"has '{node.value}' is word-boundary aware in KQL. "
                f"SQL LIKE '%{node.value}%' matches partial words too."
            )
            notes.append(f"where col has '{node.value}' → WHERE col LIKE '% {node.value} %' [⚠ word-boundary lost]")
        elif node.op == "contains":
            notes.append(f"where col contains '{node.value}' → WHERE col LIKE '%{node.value}%'")
        elif node.op == "startswith":
            notes.append(f"where col startswith '{node.value}' → WHERE col LIKE '{node.value}%'")
        elif node.op == "endswith":
            notes.append(f"where col endswith '{node.value}' → WHERE col LIKE '%{node.value}'")

    elif isinstance(node, InExpr):
        if node.negated:
            notes.append("where col !in (...) → WHERE col NOT IN (...)")
        else:
            notes.append("where col in (...) → WHERE col IN (...)")

    elif isinstance(node, SubqueryInExpr):
        tbl = node.subquery.table if hasattr(node.subquery, 'table') else "subquery"
        if node.negated:
            notes.append(f"where col !in (Table | ...) → WHERE col NOT IN (SELECT ... FROM {tbl})")
        else:
            notes.append(f"where col in (Table | ...) → WHERE col IN (SELECT ... FROM {tbl})")

    elif isinstance(node, LogicalOp):
        _walk_condition(node.left, notes, warnings)
        _walk_condition(node.right, notes, warnings)


def _annotate_bin(amount: int, unit: str, notes: list[str], warnings: list[str]) -> None:
    if unit == "d" and amount >= 7:
        warnings.append(
            f"bin(col, {amount}d) buckets from Unix epoch (Thu Jan 1 1970), "
            f"not calendar {'weeks' if amount == 7 else f'{amount}-day periods'}. "
            f"Use DATE_TRUNC('week', col) for Monday-aligned weeks."
        )
        notes.append(
            f"bin(col, {amount}d) → DATEADD/FLOOR logic [⚠ epoch-relative, not calendar weeks]"
        )
    else:
        unit_map = {"d": "day", "h": "hour", "m": "minute", "s": "second"}
        sql_unit = unit_map.get(unit, unit)
        notes.append(f"bin(col, {amount}{unit}) → DATE_TRUNC('{sql_unit}', col)")


def _expr_note(expr) -> str:
    if isinstance(expr, AgoExpr):
        return f"ago({expr.amount}{expr.unit})"
    if isinstance(expr, IffExpr):
        return "iff(condition, true_val, false_val)"
    if hasattr(expr, 'name'):
        return str(expr.name)
    if hasattr(expr, 'value'):
        return str(expr.value)
    return type(expr).__name__


# ─── Annotated SQL builder ────────────────────────────────────────────────────

def _build_annotated_sql(sql: str, notes: list[str], warnings: list[str]) -> str:
    """
    Prepend a header comment block to the SQL with all annotations.
    """
    lines = ["/* KQLBridge Translation Annotations"]
    lines.append(" * " + "─" * 50)
    for i, note in enumerate(notes, 1):
        lines.append(f" * {i:2}. {note}")
    if warnings:
        lines.append(" *")
        lines.append(" * ⚠  Semantic drift warnings:")
        for w in warnings:
            # wrap at 70 chars
            words = w.split()
            line = " *    "
            for word in words:
                if len(line) + len(word) > 75:
                    lines.append(line.rstrip())
                    line = " *    " + word + " "
                else:
                    line += word + " "
            lines.append(line.rstrip())
    lines.append(" */")
    lines.append("")
    lines.append(sql)
    return "\n".join(lines)


# ─── Public API ──────────────────────────────────────────────────────────────

def explain(kql: str, target: str = "spark") -> ExplainResult:
    """
    Translate KQL and return annotated SQL with inline explanations.

    Args:
        kql:    KQL query string
        target: "spark" (default) or "tsql"

    Returns:
        ExplainResult with .annotated_sql, .summary, .annotations, .warnings
    """
    from .parser import parse
    from lark.exceptions import UnexpectedInput as _LarkUnexpectedInput
    from .generators.spark_sql import SparkSQLGenerator
    from .generators.tsql import TSQLGenerator

    try:
        query = parse(kql)
    except _LarkUnexpectedInput as e:
        raise ValueError(
            f"Unsupported KQL syntax. Use is_supported() to check first.\n{e}"
        ) from None

    gen = TSQLGenerator() if target == "tsql" else SparkSQLGenerator()
    sql = gen.generate(query)

    notes, warnings = _annotate_query(query)
    annotated = _build_annotated_sql(sql, notes, warnings)

    return ExplainResult(
        kql=kql,
        sql=sql,
        annotated_sql=annotated,
        annotations=notes,
        warnings=warnings,
    )
