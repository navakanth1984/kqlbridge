"""
generators/tsql.py — KQL AST → T-SQL
=====================================
AGENT MODIFIABLE — v0.2 target (Fabric SQL Warehouse, Synapse Analytics).

Inherits ~85% of logic from SparkSQLGenerator.
Overrides only the 4 methods where T-SQL syntax diverges:

    1. _assemble     — TOP n in SELECT clause, not LIMIT n at end
    2. _render_bin   — DATEADD/DATEDIFF instead of DATE_TRUNC / TIMESTAMP_SECONDS
    3. _expr/AgoExpr — DATEADD(unit, -n, GETDATE()) instead of CURRENT_TIMESTAMP - INTERVAL
    4. _expr/BoolLit — 1/0 instead of TRUE/FALSE (T-SQL has no boolean literals)
"""

from __future__ import annotations
import re

from ..ast_nodes import AgoExpr, BinExpr, DatetimeLit, BoolLit
from .spark_sql import SparkSQLGenerator

# KQL timespan unit → T-SQL DATEADD unit
_TSQL_DATEADD_UNIT = {
    "d":  "day",
    "h":  "hour",
    "m":  "minute",
    "s":  "second",
    "ms": "millisecond",
}


class TSQLGenerator(SparkSQLGenerator):
    """
    Generates T-SQL from a KQLQuery AST.
    Inherits from SparkSQLGenerator — overrides only T-SQL-specific methods.

    Key differences from Spark SQL:
    - LIMIT n         → TOP n  (in SELECT clause, not end of query)
    - DATE_TRUNC      → DATEADD(unit, DATEDIFF(unit, 0, col), 0)
    - INTERVAL expr   → DATEADD(unit, -n, GETDATE())
    - TIMESTAMP '...' → CONVERT(datetime, '...')
    - TRUE/FALSE      → 1/0
    """

    # ─── Override 1: TOP n instead of LIMIT n ────────────────────────────

    def _assemble(
        self,
        select_cols: list[str],
        table: str,
        where_clauses: list[str],
        group_by: list[str],
        order: str,
        limit: str,
        distinct: bool,
    ) -> str:
        distinct_kw = "DISTINCT " if distinct else ""

        # Extract n from "LIMIT n" → "TOP n" in SELECT clause
        top_clause = ""
        if limit:
            m = re.search(r"\d+", limit)
            if m:
                top_clause = f"TOP {m.group()} "

        parts = [
            f"SELECT {top_clause}{distinct_kw}{', '.join(select_cols)}",
            f"FROM {table}",
        ]
        if where_clauses:
            parts.append("WHERE " + " AND ".join(where_clauses))
        if group_by:
            parts.append("GROUP BY " + ", ".join(group_by))
        if order:
            parts.append(order)
        # No LIMIT at end — TOP is already in SELECT
        return "\n".join(parts)

    # ─── Override 2: bin() → DATEADD/DATEDIFF truncation ────────────────

    def _render_bin(self, col: str, amount: int, unit: str) -> str:
        """
        T-SQL timestamp bucketing via DATEADD/DATEDIFF pattern.
        Standard: DATEADD(unit, DATEDIFF(unit, 0, col), 0)
        Multi-unit: integer division via DATEDIFF in seconds.
        """
        tsql_unit = _TSQL_DATEADD_UNIT.get(unit, unit)

        if amount == 1:
            return f"DATEADD({tsql_unit}, DATEDIFF({tsql_unit}, 0, {col}), 0)"

        # Multi-unit bins: floor via integer division
        if unit == "m":
            total_seconds = amount * 60
            return (
                f"DATEADD(second, "
                f"(DATEDIFF(second, 0, {col}) / {total_seconds}) * {total_seconds}, 0)"
            )
        if unit == "h":
            total_minutes = amount * 60
            return (
                f"DATEADD(minute, "
                f"(DATEDIFF(minute, 0, {col}) / {total_minutes}) * {total_minutes}, 0)"
            )
        if unit == "d":
            return (
                f"DATEADD(day, "
                f"(DATEDIFF(day, 0, {col}) / {amount}) * {amount}, 0)"
            )

        return f"DATEADD({tsql_unit}, DATEDIFF({tsql_unit}, 0, {col}), 0)"

    # ─── Override 3+4: T-SQL-specific expr rendering ─────────────────────

    def _expr(self, expr) -> str:
        """
        T-SQL expression rendering.
        Handles AgoExpr, DatetimeLit, BinExpr, BoolLit differently.
        All other types delegate to SparkSQLGenerator._expr().
        """
        if isinstance(expr, AgoExpr):
            unit = _TSQL_DATEADD_UNIT.get(expr.unit, expr.unit)
            return f"DATEADD({unit}, -{expr.amount}, GETDATE())"

        if isinstance(expr, DatetimeLit):
            inner = expr.raw.replace("datetime(", "").rstrip(")")
            return f"CONVERT(datetime, '{inner}')"

        if isinstance(expr, BinExpr):
            col = self._expr(expr.col)
            return self._render_bin(col, expr.amount, expr.unit)

        if isinstance(expr, BoolLit):
            # T-SQL has no TRUE/FALSE literals
            return "1" if expr.value else "0"

        from ..ast_nodes import ColumnRef
        if isinstance(expr, ColumnRef) and expr.name.lower() in ("true", "false"):
            return "1" if expr.name.lower() == "true" else "0"

        return super()._expr(expr)

    def _func_call(self, expr) -> str:
        if expr.name.lower() == "datetime":
            arg_sql = self._expr(expr.args[0])
            return f"CONVERT(datetime, {arg_sql})"
        return super()._func_call(expr)
