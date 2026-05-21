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

from ..ast_nodes import (
    AgoExpr, BinExpr, DatetimeLit, BoolLit, HasAnyExpr, StringLit,
    AggPercentile, AggMakeList, AggSumIf, AggAvgIf, AggMaxIf, AggMinIf, AggDCountIf,
)
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

        # If the table is already a UNION block, wrap it as a subquery
        is_union = "union" in table.lower()
        has_trailing = bool(order or limit or top_clause or where_clauses or group_by or distinct or select_cols != ["*"])
        if is_union and has_trailing:
            table = "(\n" + table + "\n) _union_result"

        from_clause = f"FROM {table}"
        if getattr(self, "_mv_expand_col", None):
            from_clause += f" CROSS APPLY OPENJSON({self._mv_expand_col})"

        parts = [
            f"SELECT {top_clause}{distinct_kw}{', '.join(select_cols)}",
            from_clause,
        ]
        if where_clauses:
            parts.append("WHERE " + " AND ".join(where_clauses))
        if group_by:
            parts.append("GROUP BY " + ", ".join(group_by))
        if order:
            parts.append(order)
        return "\n".join(parts)

    # ─── Override 2: bin() → DATEADD/DATEDIFF truncation ────────────────

    def _render_bin(self, col: str, amount: int, unit: str) -> str:
        tsql_unit = _TSQL_DATEADD_UNIT.get(unit, unit)

        if amount == 1:
            return f"DATEADD({tsql_unit}, DATEDIFF({tsql_unit}, 0, {col}), 0)"

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
        if isinstance(expr, AgoExpr):
            unit = _TSQL_DATEADD_UNIT.get(expr.unit, expr.unit)
            return f"DATEADD({unit}, -{expr.amount}, GETDATE())"

        if isinstance(expr, DatetimeLit):
            # FIX-01: extract the ISO date string directly from the raw literal
            # e.g. DatetimeLit(raw="datetime('2024-01-01')") → CAST('2024-01-01' AS DATETIME2)
            inner = expr.raw.replace("datetime(", "").rstrip(")")
            inner = inner.strip("'\"")
            return f"CAST('{inner}' AS DATETIME2)"

        if isinstance(expr, BinExpr):
            col = self._expr(expr.col)
            return self._render_bin(col, expr.amount, expr.unit)

        if isinstance(expr, BoolLit):
            return "1" if expr.value else "0"

        from ..ast_nodes import ColumnRef
        if isinstance(expr, ColumnRef) and expr.name.lower() in ("true", "false"):
            return "1" if expr.name.lower() == "true" else "0"

        return super()._expr(expr)

    def _func_call(self, expr) -> str:
        name = expr.name.lower()
        args = [self._expr(a) for a in expr.args]
        if name == "datetime":
            # FIX-01: args[0] is the already-rendered date string (quoted by pre-processor)
            # Strip surrounding quotes and emit CAST('...' AS DATETIME2)
            date_str = args[0].strip("'\"") if args else ""
            return f"CAST('{date_str}' AS DATETIME2)"
        if name == "split":
            return f"STRING_SPLIT({args[0]}, {args[1]})"
        if name == "datetime_add":
            period = args[0].strip("'\"").lower()
            unit_map = {
                "year": "year",
                "month": "month",
                "day": "day",
                "hour": "hour",
                "minute": "minute",
                "second": "second",
            }
            tsql_unit = unit_map.get(period, period)
            return f"DATEADD({tsql_unit}, {args[1]}, {args[2]})"
        if name == "datetime_diff":
            period = args[0].strip("'\"").lower()
            unit_map = {
                "year": "year",
                "month": "month",
                "day": "day",
                "hour": "hour",
                "minute": "minute",
                "second": "second",
            }
            tsql_unit = unit_map.get(period, period)
            return f"DATEDIFF({tsql_unit}, {args[2]}, {args[1]})"
        if name == "strcat_delim":
            return f"CONCAT_WS({args[0]}, {', '.join(args[1:])})"
        if name == "parse_json_path":
            path = args[1].strip("'\"")
            return f"JSON_VALUE({args[0]}, '$.{path}')"
        if name == "ipv4_is_private":
            return self._render_ipv4_is_private(args)
        if name == "ipv4_is_in_range":
            return self._render_ipv4_is_in_range(args)
        if name == "tostring":
            return f"CAST({args[0]} AS NVARCHAR(MAX))"
        if name == "toint":
            return f"CAST({args[0]} AS INT)"
        if name == "tolong":
            return f"CAST({args[0]} AS BIGINT)"
        if name == "todouble":
            return f"CAST({args[0]} AS FLOAT)"
        if name == "format_datetime":
            return f"FORMAT({args[0]}, {args[1]})"
        if name == "array_length":
            return f"COALESCE((SELECT COUNT(*) FROM OPENJSON({args[0]})), 0)"
        if name == "array_index_of":
            val = args[1] if len(args) >= 2 else "NULL"
            return f"COALESCE((SELECT MIN(CAST([key] AS INT)) FROM OPENJSON({args[0]}) WHERE [value] = {val}), -1)"
        return super()._func_call(expr)

    def _bool_expr(self, expr) -> str:
        if isinstance(expr, HasAnyExpr):
            col = self._expr(expr.col)
            parts = []
            for v in expr.values:
                if isinstance(v, StringLit):
                    val_str = v.value
                else:
                    val_str = self._expr(v).strip("'\"")
                parts.append(f"{col} LIKE '%{val_str}%'")
            return f"({' OR '.join(parts)})"
        return super()._bool_expr(expr)

    def _agg(self, agg) -> str:
        alias_suffix = f" AS {agg.alias}" if getattr(agg, "alias", None) else ""
        if isinstance(agg, AggPercentile):
            pct_val = self._expr(agg.percentile)
            try:
                numeric_pct = float(pct_val)
                pct_expr = str(numeric_pct / 100.0)
            except ValueError:
                pct_expr = f"{pct_val} / 100.0"
            col_expr = self._expr(agg.col)
            return f"PERCENTILE_CONT({pct_expr}) WITHIN GROUP (ORDER BY {col_expr}){alias_suffix}"
        if isinstance(agg, AggMakeList):
            col_expr = self._expr(agg.col)
            return f"STRING_AGG({col_expr}, ','){alias_suffix}"

        if isinstance(agg, AggSumIf):
            cond = self._bool_expr(agg.condition)
            col = self._expr(agg.col)
            return f"SUM(CASE WHEN {cond} THEN {col} END){alias_suffix}"

        if isinstance(agg, AggAvgIf):
            cond = self._bool_expr(agg.condition)
            col = self._expr(agg.col)
            return f"AVG(CASE WHEN {cond} THEN {col} END){alias_suffix}"

        if isinstance(agg, AggMaxIf):
            cond = self._bool_expr(agg.condition)
            col = self._expr(agg.col)
            return f"MAX(CASE WHEN {cond} THEN {col} END){alias_suffix}"

        if isinstance(agg, AggMinIf):
            cond = self._bool_expr(agg.condition)
            col = self._expr(agg.col)
            return f"MIN(CASE WHEN {cond} THEN {col} END){alias_suffix}"

        if isinstance(agg, AggDCountIf):
            cond = self._bool_expr(agg.condition)
            col = self._expr(agg.col)
            return f"COUNT(DISTINCT CASE WHEN {cond} THEN {col} END){alias_suffix}"
        return super()._agg(agg)

    def _render_ipv4_is_private(self, args: list[str]) -> str:
        ip = args[0]
        ip_int = (
            f"(CAST(PARSENAME({ip}, 4) AS BIGINT) * 16777216 + "
            f"CAST(PARSENAME({ip}, 3) AS BIGINT) * 65536 + "
            f"CAST(PARSENAME({ip}, 2) AS BIGINT) * 256 + "
            f"CAST(PARSENAME({ip}, 1) AS BIGINT))"
        )
        return (
            f"(({ip_int} BETWEEN 167772160 AND 184549375) OR "
            f"({ip_int} BETWEEN 2886729728 AND 2887778303) OR "
            f"({ip_int} BETWEEN 3232235520 AND 3232301055) OR "
            f"({ip_int} BETWEEN 2130706432 AND 2147483647))"
        )

    def _render_ipv4_is_in_range(self, args: list[str]) -> str:
        ip = args[0]
        cidr = args[1].strip("'\"")
        try:
            ip_part, mask_part = cidr.split('/')
            mask = int(mask_part)
            octets = [int(o) for o in ip_part.split('.')]
            ip_val = (octets[0] << 24) + (octets[1] << 16) + (octets[2] << 8) + octets[3]
            network_mask = (0xFFFFFFFF << (32 - mask)) & 0xFFFFFFFF
            start = ip_val & network_mask
            end = start | (network_mask ^ 0xFFFFFFFF)
        except Exception:
            return f"ipv4_is_in_range({ip}, '{cidr}')"
            
        ip_int = (
            f"(CAST(PARSENAME({ip}, 4) AS BIGINT) * 16777216 + "
            f"CAST(PARSENAME({ip}, 3) AS BIGINT) * 65536 + "
            f"CAST(PARSENAME({ip}, 2) AS BIGINT) * 256 + "
            f"CAST(PARSENAME({ip}, 1) AS BIGINT))"
        )
        return f"({ip_int} BETWEEN {start} AND {end})"
