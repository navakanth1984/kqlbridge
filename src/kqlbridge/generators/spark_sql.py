"""
generators/spark_sql.py — KQL AST → Spark SQL
==============================================
AGENT MODIFIABLE — This is the primary v0.1 generator.

Rules for the agent:
1. One method per operator. Do not merge operators into shared logic
   until the same pattern appears ≥ 3 times.
2. Every change must trace to a failing benchmark case ID.
3. Do not refactor adjacent passing methods while fixing a failing one.
4. After each change: run prepare.py and state the score delta.
5. Karpathy Principle 2: if a method exceeds ~30 lines, question it first.

Karpathy Principle 5 — Jagged Intelligence Warning:
The summarize → GROUP BY rewrite is the highest-risk semantic translation.
KQL summarize is left-to-right; SQL GROUP BY requires column names in SELECT.
Human review is REQUIRED on every aggregate operator before accepting it as passing.
"""

from __future__ import annotations

from ..ast_nodes import (
    KQLQuery, LetBinding,
    WhereOp, ProjectOp, SummarizeOp, OrderOp, TakeOp,
    DistinctOp, ExtendOp, JoinOp, UnionOp, CountOp,
    AggCount, AggSum, AggAvg, AggMin, AggMax, AggDCount, AggCountIf,
    BinGroup, PlainGroup,
    ColumnRef, StringLit, IntLit, FloatLit, BoolLit, AgoExpr, BinExpr,
    FuncCall, BinaryOp,
    Comparison, InExpr, StringOp, NullCheck, LogicalOp, Negation, IffExpr,
    DatetimeLit,
)

# KQL timespan unit → SQL INTERVAL unit
_INTERVAL_UNIT = {
    "d": "days",
    "h": "hours",
    "m": "minutes",
    "s": "seconds",
    "ms": "milliseconds",
}

# KQL bin() timespan unit → DATE_TRUNC granularity
_DATE_TRUNC_UNIT = {
    "d": "day",
    "h": "hour",
    "m": "minute",
    "s": "second",
}

# KQL comparison operators → SQL
_COMP_OP_MAP = {
    "==": "=",
    "!=": "<>",
    "=~": "=",   # case-insensitive — note: exact only in v0.1
    "<":  "<",
    "<=": "<=",
    ">":  ">",
    ">=": ">=",
}


class SparkSQLGenerator:
    """
    Generates Spark SQL from a KQLQuery AST.

    Usage:
        gen = SparkSQLGenerator()
        sql = gen.generate(query)
    """

    def generate(self, query: KQLQuery) -> str:
        """Entry point. Returns a Spark SQL string."""
        ctes = self._build_ctes(query.let_bindings)
        body = self._build_body(query)

        if ctes:
            return f"WITH {', '.join(ctes)}\n{body}"
        return body

    # ─── CTE Layer (let bindings) ─────────────────────────────────────────

    def _build_ctes(self, bindings: list[LetBinding]) -> list[str]:
        """Convert let bindings → WITH ... AS (...) CTEs."""
        ctes = []
        for binding in bindings:
            sub_sql = self._build_body(binding.value)
            ctes.append(f"{binding.name} AS (\n  {sub_sql}\n)")
        return ctes

    # ─── Body Builder ────────────────────────────────────────────────────

    def _build_body(self, query: KQLQuery) -> str:
        """
        Walk the pipe operators and accumulate SQL clause fragments.
        The assembly order is: SELECT … FROM … WHERE … GROUP BY … ORDER BY … LIMIT
        """
        table = query.table
        select_cols: list[str] = ["*"]
        where_clauses: list[str] = []
        group_by: list[str] = []
        order: str = ""
        limit: str = ""
        distinct: bool = False

        for op in query.pipes:

            if isinstance(op, WhereOp):
                where_clauses.append(self._where(op))

            elif isinstance(op, ProjectOp):
                aliases = op.aliases or {}
                select_cols = [
                    f"{col} AS {aliases[col]}" if col in aliases else col
                    for col in op.columns
                ]

            elif isinstance(op, SummarizeOp):
                select_cols, group_by = self._summarize(op)

            elif isinstance(op, OrderOp):
                order = self._order(op)

            elif isinstance(op, TakeOp):
                limit = f"LIMIT {op.n}"

            elif isinstance(op, DistinctOp):
                distinct = True
                if op.columns:
                    select_cols = op.columns

            elif isinstance(op, ExtendOp):
                # Extend: keep existing cols + add computed cols
                extend_parts = [f"{self._expr(expr)} AS {alias}"
                                for alias, expr in op.assignments]
                if select_cols == ["*"]:
                    select_cols = ["*"] + extend_parts
                else:
                    select_cols = select_cols + extend_parts
                # If a summarize follows, we must wrap the current state in a subquery
                # so the extended columns are visible to GROUP BY / agg functions
                future_ops = query.pipes[query.pipes.index(op) + 1:]
                if any(isinstance(f, (SummarizeOp, ProjectOp)) for f in future_ops):
                    inner_sql = self._assemble(
                        select_cols=select_cols,
                        table=table,
                        where_clauses=where_clauses,
                        group_by=[],
                        order="",
                        limit="",
                        distinct=False,
                    )
                    table = "(\n" + inner_sql + "\n) _extended"
                    select_cols = ["*"]
                    where_clauses = []

            elif isinstance(op, JoinOp):
                # Inline join — handled in assembly
                join_sql = self._join(table, op, where_clauses)
                # NOTE: do NOT clear where_clauses — WHERE filters from before
                # the join should still appear in the final WHERE clause.
                table = join_sql   # replace table with joined expression
                select_cols = ["*"]

            elif isinstance(op, UnionOp):
                union_sql = self._union(table, op)
                if union_sql != table:  # real union was built
                    table = union_sql
                    select_cols = ["*"]
                    # Check if this is the last op — return union directly if no trailing ops
                    remaining = query.pipes[query.pipes.index(op) + 1:]
                    if not remaining:
                        return union_sql
                # if union_sql == table, op.tables was empty → unsupported subquery union

            elif isinstance(op, CountOp):
                select_cols = ["COUNT(*) AS count_"]

        return self._assemble(
            select_cols=select_cols,
            table=table,
            where_clauses=where_clauses,
            group_by=group_by,
            order=order,
            limit=limit,
            distinct=distinct,
        )

    # ─── Clause Builders ────────────────────────────────────────────────────

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

        # If the table is already a UNION ALL block, wrap it as a subquery
        # so ORDER BY and LIMIT can be applied to the combined result
        # If table is a UNION ALL block, wrap in subquery only when trailing ops exist
        if "UNION ALL" in table and (order or limit or where_clauses or group_by):
            table = "(\n" + table + "\n) _union_result"

        parts = [
            f"SELECT {distinct_kw}{', '.join(select_cols)}",
            f"FROM {table}",
        ]
        if where_clauses:
            parts.append("WHERE " + " AND ".join(where_clauses))
        if group_by:
            parts.append("GROUP BY " + ", ".join(group_by))
        if order:
            parts.append(order)
        if limit:
            parts.append(limit)
        return "\n".join(parts)

    def _where(self, op: WhereOp) -> str:
        return self._bool_expr(op.condition)

    def _summarize(self, op: SummarizeOp) -> tuple[list[str], list[str]]:
        """
        Returns (select_cols, group_by_cols).

        Karpathy P5 — Jagged Intelligence note:
        KQL summarize puts aggregations first, then group-by columns.
        SQL SELECT must include group-by columns + aggregation expressions.
        The generator handles this rewrite: group-by cols come first in SELECT,
        then aggregation columns. Human review required on every case.
        """
        group_by_cols: list[str] = []
        group_by_exprs: list[str] = []

        for gb in op.group_by:
            if isinstance(gb, BinGroup):
                col_sql = self._expr(gb.col)
                gb_expr = self._render_bin(col_sql, gb.amount, gb.unit)
                col_alias = col_sql
                group_by_exprs.append(gb_expr)
                group_by_cols.append(f"{gb_expr} AS {col_alias}")
            elif isinstance(gb, PlainGroup):
                col_sql = self._expr(gb.col)
                group_by_exprs.append(col_sql)
                group_by_cols.append(col_sql)

        agg_cols: list[str] = []
        for agg in op.aggregations:
            agg_cols.append(self._agg(agg))

        # SQL SELECT: group-by columns first, then aggregations
        select_cols = group_by_cols + agg_cols

        return select_cols, group_by_exprs

    def _agg(self, agg) -> str:
        """Render a single aggregation expression."""
        alias_suffix = f" AS {agg.alias}" if getattr(agg, "alias", None) else ""

        if isinstance(agg, AggCount):
            return f"COUNT(*){alias_suffix}"
        if isinstance(agg, AggSum):
            return f"SUM({self._expr(agg.col)}){alias_suffix}"
        if isinstance(agg, AggAvg):
            return f"AVG({self._expr(agg.col)}){alias_suffix}"
        if isinstance(agg, AggMin):
            return f"MIN({self._expr(agg.col)}){alias_suffix}"
        if isinstance(agg, AggMax):
            return f"MAX({self._expr(agg.col)}){alias_suffix}"
        if isinstance(agg, AggDCount):
            return f"COUNT(DISTINCT {self._expr(agg.col)}){alias_suffix}"
        if isinstance(agg, AggCountIf):
            cond = self._bool_expr(agg.condition)
            return f"COUNT(CASE WHEN {cond} THEN 1 END){alias_suffix}"

        raise NotImplementedError(f"Unknown aggregation type: {type(agg).__name__}")

    def _order(self, op: OrderOp) -> str:
        items = [f"{self._expr(item.col)} {item.direction.upper()}"
                 for item in op.items]
        return "ORDER BY " + ", ".join(items)

    def _join(self, left_table: str, op: JoinOp, existing_wheres: list[str]) -> str:
        """
        KQL join → SQL INNER/LEFT/RIGHT/FULL JOIN.
        Returns a 'table expression' that replaces the FROM clause.
        Note: existing WHERE clauses from before the join are moved into ON.
        """
        kind_map = {
            "inner":      "INNER JOIN",
            "leftouter":  "LEFT OUTER JOIN",
            "rightouter": "RIGHT OUTER JOIN",
            "fullouter":  "FULL OUTER JOIN",
        }
        join_kw = kind_map.get(op.kind, "INNER JOIN")
        right_table = op.right.table
        on_clause = " AND ".join(
            f"{left_table}.{k} = {right_table}.{k}" for k in op.keys
        )
        return f"{left_table}\n{join_kw} {right_table} ON {on_clause}"

    def _union(self, table: str, op: UnionOp) -> str:
        """KQL union T1, T2, T3 → SELECT * FROM T1 UNION ALL SELECT * FROM T2 ..."""
        if not op.tables:
            return table  # subquery union — return unchanged
        if "UNION ALL" in table:
            # table is already a union block (chained union) — append without re-wrapping
            new_parts = ["UNION ALL\nSELECT * FROM " + t for t in op.tables]
            return table + "\n" + "\n".join(new_parts)
        all_tables = [table] + list(op.tables)
        parts = [f"SELECT * FROM {t}" for t in all_tables]
        return "\nUNION ALL\n".join(parts)

    # ─── Expression Renderers ────────────────────────────────────────────────

    def _render_bin(self, col: str, amount: int, unit: str) -> str:
        """
        Render bin(col, N<unit>) → Spark SQL timestamp bucketing.
        - Hourly or coarser  →  DATE_TRUNC
        - Sub-hour multi-minute (e.g. 5m=300s)  →  TIMESTAMP_SECONDS FLOOR
        - Single minute (1m) or second  →  DATE_TRUNC('minute'/'second', ...)
        """
        seconds_per_unit = {"d": 86400, "h": 3600, "m": 60, "s": 1}
        if unit in ("d", "h") or (unit == "m" and amount == 1) or unit == "s":
            trunc = _DATE_TRUNC_UNIT.get(unit, unit)
            return f"DATE_TRUNC('{trunc}', {col})"
        # Multi-minute or other sub-hour bins → FLOOR
        total_seconds = amount * seconds_per_unit.get(unit, 1)
        return (f"TIMESTAMP_SECONDS("
                f"FLOOR(UNIX_TIMESTAMP({col}) / {total_seconds})"
                f" * {total_seconds})")

    def _expr(self, expr) -> str:
        """Render a scalar expression to SQL."""

        if isinstance(expr, ColumnRef):
            return expr.name

        if isinstance(expr, StringLit):
            return f"'{expr.value}'"

        if isinstance(expr, IntLit):
            return str(expr.value)

        if isinstance(expr, FloatLit):
            return str(expr.value)

        if isinstance(expr, BoolLit):
            return "TRUE" if expr.value else "FALSE"

        if isinstance(expr, AgoExpr):
            unit = _INTERVAL_UNIT.get(expr.unit, expr.unit)
            return f"CURRENT_TIMESTAMP - INTERVAL '{expr.amount} {unit}'"

        if isinstance(expr, BinExpr):
            col = self._expr(expr.col)
            return self._render_bin(col, expr.amount, expr.unit)

        if isinstance(expr, BinaryOp):
            return f"({self._expr(expr.left)} {expr.op} {self._expr(expr.right)})"

        if isinstance(expr, Comparison):
            # Comparison used as a scalar (e.g. extend IsLarge = Amount > 1000)
            # Render as direct SQL comparison expression
            op_map = {"==": "=", "=~": "=", "!=": "!=",
                      "<": "<", ">": ">", "<=": "<=", ">=": ">="}
            sql_op = op_map.get(expr.op, expr.op)
            return f"({self._expr(expr.left)} {sql_op} {self._expr(expr.right)})"

        if isinstance(expr, FuncCall):
            return self._func_call(expr)

        if isinstance(expr, DatetimeLit):
            # datetime(2024-01-01) → TIMESTAMP '2024-01-01'
            inner = expr.raw.replace("datetime(", "").rstrip(")")
            return f"TIMESTAMP '{inner}'"

        if isinstance(expr, str):
            return expr

        if isinstance(expr, IffExpr):
            cond = self._bool_expr(expr.condition)
            true_v = self._expr(expr.true_val)
            false_v = self._expr(expr.false_val)
            return f"CASE WHEN {cond} THEN {true_v} ELSE {false_v} END"

        raise NotImplementedError(f"Unknown expr type: {type(expr).__name__}")

    def _func_call(self, expr: FuncCall) -> str:
        """
        Map KQL built-in functions to Spark SQL equivalents.
        Only functions needed for the 14 v0.1 operators are mapped here.
        Add new mappings only when a benchmark case requires them.
        """
        name = expr.name.lower()
        args = [self._expr(a) for a in expr.args]

        kql_to_spark = {
            "tostring":    lambda a: f"CAST({a[0]} AS STRING)",
            "toint":       lambda a: f"CAST({a[0]} AS INT)",
            "tolong":      lambda a: f"CAST({a[0]} AS BIGINT)",
            "todouble":    lambda a: f"CAST({a[0]} AS DOUBLE)",
            "strlen":      lambda a: f"LENGTH({a[0]})",
            "tolower":     lambda a: f"LOWER({a[0]})",
            "toupper":     lambda a: f"UPPER({a[0]})",
            "trim":        lambda a: f"TRIM({a[0]})",
            "replace":     lambda a: f"REPLACE({a[0]}, {a[1]}, {a[2]})",
            "substring":   lambda a: f"SUBSTRING({a[0]}, {a[1]}, {a[2]})",
            "strcat":      lambda a: " || ".join(a),
            "now":         lambda a: "CURRENT_TIMESTAMP",
            "startofday":  lambda a: f"DATE_TRUNC('day', {a[0]})",
            "startofhour": lambda a: f"DATE_TRUNC('hour', {a[0]})",
            "startofmonth":lambda a: f"DATE_TRUNC('month', {a[0]})",
            "startofyear": lambda a: f"DATE_TRUNC('year', {a[0]})",
            "format_datetime": lambda a: f"DATE_FORMAT({a[0]}, {a[1]})",
            "dayofweek":   lambda a: f"DAYOFWEEK({a[0]})",
            "hourofday":   lambda a: f"HOUR({a[0]})",
        }

        if name in kql_to_spark:
            return kql_to_spark[name](args)

        # Unknown function — pass through as-is with a comment
        args_str = ", ".join(args)
        return f"{name}({args_str}) /* KQL function — verify Spark equivalent */"

    # ─── Boolean Expression Renderers ────────────────────────────────────────

    def _bool_expr(self, expr) -> str:
        """Render a boolean expression to a SQL WHERE fragment."""

        if isinstance(expr, Comparison):
            left = self._expr(expr.left)
            right = self._expr(expr.right)
            op = _COMP_OP_MAP.get(expr.op, expr.op)
            return f"{left} {op} {right}"

        if isinstance(expr, InExpr):
            col = self._expr(expr.col)
            values = ", ".join(self._expr(v) for v in expr.values)
            not_kw = "NOT " if expr.negated else ""
            return f"{col} {not_kw}IN ({values})"

        if isinstance(expr, StringOp):
            col = self._expr(expr.col)
            val = f"'{expr.value}'"
            op_map = {
                "has":        f"{col} LIKE '% {expr.value} %'",
                "contains":   f"{col} LIKE '%{expr.value}%'",
                "startswith": f"{col} LIKE '{expr.value}%'",
                "endswith":   f"{col} LIKE '%{expr.value}'",
                "matches regex": f"regexp_like({col}, {val})",
            }
            return op_map.get(expr.op, f"{col} LIKE '%{expr.value}%'")

        if isinstance(expr, NullCheck):
            col = self._expr(expr.col)
            return f"{col} IS NULL" if expr.is_null else f"{col} IS NOT NULL"

        if isinstance(expr, LogicalOp):
            left = self._bool_expr(expr.left)
            right = self._bool_expr(expr.right)
            return f"({left} {expr.op.upper()} {right})"

        if isinstance(expr, Negation):
            return f"NOT ({self._bool_expr(expr.expr)})"

        raise NotImplementedError(f"Unknown bool expr type: {type(expr).__name__}")
