"""
generators/spark_sql.py — KQL AST → Spark SQL
==============================================
Ported from document 11 of the kqlbridge codebase.
AGENT MODIFIABLE — primary v0.1 generator.
"""

from __future__ import annotations
import ipaddress
from ..schema_hint import SchemaHint
from ..ast_nodes import (
    KQLQuery, LetBinding,
    WhereOp, ProjectOp, SummarizeOp, OrderOp, TakeOp,
    DistinctOp, ExtendOp, JoinOp, UnionOp, CountOp, SerializeOp,
    AggCount, AggSum, AggAvg, AggMin, AggMax, AggDCount, AggCountIf,
    AggSumIf, AggAvgIf, AggMaxIf, AggMinIf, AggDCountIf, AggPercentile, AggMakeList,
    BinGroup, PlainGroup,
    ColumnRef, StringLit, IntLit, FloatLit, BoolLit, AgoExpr, BinExpr,
    FuncCall, BinaryOp,
    Comparison, InExpr, StringOp, NullCheck, LogicalOp, Negation, IffExpr,
    SubqueryInExpr, DatetimeLit, HasAnyExpr,
)

_INTERVAL_UNIT = {"d":"days","h":"hours","m":"minutes","s":"seconds","ms":"milliseconds"}
_DATE_TRUNC_UNIT = {"d":"day","h":"hour","m":"minute","s":"second"}
_COMP_OP_MAP = {"==":"=","!=":"<>","=~":"=","<":"<","<=":"<=",">":">",">=":">="}


class SparkSQLGenerator:
    def __init__(self, hint: SchemaHint | None = None):
        self.hint = hint

    def generate(self, query: KQLQuery) -> str:
        self._scalar_bindings = {}
        self._mv_expand_col = None
        non_scalar_bindings = []
        for binding in query.let_bindings:
            if hasattr(binding.value, "scalar_expr"):
                self._scalar_bindings[binding.name] = binding.value.scalar_expr
            else:
                non_scalar_bindings.append(binding)
        ctes = self._build_ctes(non_scalar_bindings)
        body = self._build_body(query)
        if ctes:
            return f"WITH {', '.join(ctes)}\n{body}"
        return body

    def _build_ctes(self, bindings):
        ctes = []
        for binding in bindings:
            sub_sql = self._build_body(binding.value)
            ctes.append(f"{binding.name} AS (\n  {sub_sql}\n)")
        return ctes

    def _build_body(self, query: KQLQuery) -> str:
        table = query.table
        self._current_base_table = query.table
        select_cols = ["*"]
        where_clauses = []
        group_by = []
        order = ""
        limit = ""
        distinct = False
        summarize_active = False

        for idx, op in enumerate(query.pipes):
            if isinstance(op, WhereOp):
                if summarize_active:
                    inner_sql = self._assemble(select_cols, table, where_clauses, group_by, order, limit, distinct)
                    table = "(\n" + inner_sql + "\n) _filtered"
                    select_cols = ["*"]; where_clauses = [self._where(op)]
                    group_by = []; order = ""; limit = ""; distinct = False; summarize_active = False
                else:
                    where_clauses.append(self._where(op))

            elif isinstance(op, ProjectOp):
                aliases = op.aliases or {}
                select_cols = [f"{col} AS {aliases[col]}" if col in aliases else col for col in op.columns]

            elif isinstance(op, SummarizeOp):
                if summarize_active:
                    inner_sql = self._assemble(select_cols, table, where_clauses, group_by, order, limit, distinct)
                    table = "(\n" + inner_sql + "\n) _summarized"
                    select_cols = ["*"]; where_clauses = []; group_by = []; order = ""; limit = ""; distinct = False
                select_cols, group_by = self._summarize(op)
                summarize_active = True

            elif isinstance(op, OrderOp):
                order = self._order(op)

            elif isinstance(op, TakeOp):
                limit = f"LIMIT {op.n}"

            elif isinstance(op, DistinctOp):
                distinct = True
                if op.columns:
                    select_cols = op.columns

            elif isinstance(op, ExtendOp):
                if summarize_active:
                    inner_sql = self._assemble(select_cols, table, where_clauses, group_by, order, limit, distinct)
                    table = "(\n" + inner_sql + "\n) _summarized"
                    select_cols = ["*"]; where_clauses = []; group_by = []; order = ""; limit = ""; distinct = False; summarize_active = False

                mv_expand_assignment = None
                for alias, expr in op.assignments:
                    if alias == "_mv_expand" and isinstance(expr, FuncCall) and expr.name == "mv_expand_fn":
                        mv_expand_assignment = expr; break
                if mv_expand_assignment:
                    self._mv_expand_col = self._expr(mv_expand_assignment.args[0])
                else:
                    extend_parts = [f"{self._expr(expr)} AS {alias}" for alias, expr in op.assignments]
                    if select_cols == ["*"]:
                        select_cols = ["*"] + extend_parts
                    else:
                        select_cols = select_cols + extend_parts
                    future_ops = query.pipes[idx + 1:]
                    if any(isinstance(f, (SummarizeOp, ProjectOp)) for f in future_ops):
                        inner_sql = self._assemble(select_cols, table, where_clauses, [], "", "", False)
                        table = "(\n" + inner_sql + "\n) _extended"
                        select_cols = ["*"]; where_clauses = []

            elif isinstance(op, JoinOp):
                if summarize_active:
                    inner_sql = self._assemble(select_cols, table, where_clauses, group_by, order, limit, distinct)
                    table = "(\n" + inner_sql + "\n) _summarized"
                    select_cols = ["*"]; where_clauses = []; group_by = []; order = ""; limit = ""; distinct = False; summarize_active = False
                join_sql = self._join(table, op, where_clauses)
                table = join_sql; select_cols = ["*"]

            elif isinstance(op, UnionOp):
                if summarize_active:
                    inner_sql = self._assemble(select_cols, table, where_clauses, group_by, order, limit, distinct)
                    table = "(\n" + inner_sql + "\n) _summarized"
                    select_cols = ["*"]; where_clauses = []; group_by = []; order = ""; limit = ""; distinct = False; summarize_active = False
                union_sql = self._union(table, op)
                if union_sql != table:
                    table = union_sql; select_cols = ["*"]
                    remaining = query.pipes[idx + 1:]
                    if not remaining:
                        return union_sql

            elif isinstance(op, CountOp):
                select_cols = ["COUNT(*) AS count_"]

            elif isinstance(op, SerializeOp):
                pass

        return self._assemble(select_cols, table, where_clauses, group_by, order, limit, distinct)

    def _assemble(self, select_cols, table, where_clauses, group_by, order, limit, distinct):
        distinct_kw = "DISTINCT " if distinct else ""
        if "UNION ALL" in table and (order or limit or where_clauses or group_by or select_cols != ["*"]):
            table = "(\n" + table + "\n) _union_result"
        from_clause = f"FROM {table}"
        if getattr(self, "_mv_expand_col", None):
            from_clause += f" LATERAL VIEW explode({self._mv_expand_col}) AS exploded_{self._mv_expand_col}"
        parts = [f"SELECT {distinct_kw}{', '.join(select_cols)}", from_clause]
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

    def _summarize(self, op: SummarizeOp):
        group_by_cols = []; group_by_exprs = []
        for gb in op.group_by:
            if isinstance(gb, BinGroup):
                col_sql = self._expr(gb.col)
                gb_expr = self._render_bin(col_sql, gb.amount, gb.unit)
                group_by_exprs.append(gb_expr)
                group_by_cols.append(f"{gb_expr} AS {col_sql}")
            elif isinstance(gb, PlainGroup):
                col_sql = self._expr(gb.col)
                group_by_exprs.append(col_sql)
                group_by_cols.append(col_sql)
        agg_cols = [self._agg(agg) for agg in op.aggregations]
        return group_by_cols + agg_cols, group_by_exprs

    def _agg(self, agg) -> str:
        alias_suffix = f" AS {agg.alias}" if getattr(agg, "alias", None) else ""
        if isinstance(agg, AggCount): return f"COUNT(*){alias_suffix}"
        if isinstance(agg, AggSum): return f"SUM({self._expr(agg.col)}){alias_suffix}"
        if isinstance(agg, AggAvg): return f"AVG({self._expr(agg.col)}){alias_suffix}"
        if isinstance(agg, AggMin): return f"MIN({self._expr(agg.col)}){alias_suffix}"
        if isinstance(agg, AggMax): return f"MAX({self._expr(agg.col)}){alias_suffix}"
        if isinstance(agg, AggDCount): return f"COUNT(DISTINCT {self._expr(agg.col)}){alias_suffix}"
        if isinstance(agg, AggCountIf):
            cond = self._bool_expr(agg.condition)
            return f"COUNT(CASE WHEN {cond} THEN 1 END){alias_suffix}"
        if isinstance(agg, AggPercentile):
            pct = self._expr(agg.percentile)
            try: pct_expr = str(float(pct) / 100.0)
            except: pct_expr = f"{pct} / 100.0"
            return f"approx_percentile({self._expr(agg.col)}, {pct_expr}){alias_suffix}"
        if isinstance(agg, AggMakeList): return f"collect_list({self._expr(agg.col)}){alias_suffix}"
        if isinstance(agg, AggSumIf):
            return f"SUM(CASE WHEN {self._bool_expr(agg.condition)} THEN {self._expr(agg.col)} END){alias_suffix}"
        if isinstance(agg, AggAvgIf):
            return f"AVG(CASE WHEN {self._bool_expr(agg.condition)} THEN {self._expr(agg.col)} END){alias_suffix}"
        if isinstance(agg, AggMaxIf):
            return f"MAX(CASE WHEN {self._bool_expr(agg.condition)} THEN {self._expr(agg.col)} END){alias_suffix}"
        if isinstance(agg, AggMinIf):
            return f"MIN(CASE WHEN {self._bool_expr(agg.condition)} THEN {self._expr(agg.col)} END){alias_suffix}"
        if isinstance(agg, AggDCountIf):
            return f"COUNT(DISTINCT CASE WHEN {self._bool_expr(agg.condition)} THEN {self._expr(agg.col)} END){alias_suffix}"
        raise NotImplementedError(f"Unknown agg: {type(agg).__name__}")

    def _order(self, op: OrderOp) -> str:
        items = [f"{self._expr(item.col)} {item.direction.upper()}" for item in op.items]
        return "ORDER BY " + ", ".join(items)

    def _join(self, left_table, op: JoinOp, existing_wheres):
        kind_map = {"inner":"INNER JOIN","leftouter":"LEFT OUTER JOIN","rightouter":"RIGHT OUTER JOIN","fullouter":"FULL OUTER JOIN"}
        join_kw = kind_map.get(op.kind, "INNER JOIN")
        right_alias = op.right.table
        if op.right.pipes:
            old_base = getattr(self, "_current_base_table", None)
            sub_sql = self._build_body(op.right)
            self._current_base_table = old_base
            right_expr = f"(\n{sub_sql}\n) {right_alias}"
        else:
            right_expr = right_alias
        if "UNION ALL" in left_table and not left_table.strip().startswith("("):
            left_table = "(\n" + left_table + "\n) _union_result"
            left_prefix = "_union_result"
        else:
            left_prefix = getattr(self, "_current_base_table", None)
            if not left_prefix:
                first_token = left_table.strip().split()[0].strip("()")
                if first_token == "" or first_token.upper() == "SELECT":
                    last_token = left_table.strip().split()[-1]
                    if last_token and last_token != ")":
                        left_prefix = last_token
                    else:
                        left_prefix = "_union_result"
                else:
                    left_prefix = first_token

        on_clause = " AND ".join(f"{left_prefix}.{k} = {right_alias}.{k}" for k in op.keys)
        return f"{left_table}\n{join_kw} {right_expr} ON {on_clause}"

    def _union(self, table, op: UnionOp) -> str:
        if not op.tables: return table
        subqueries = op.subqueries or {}
        def _item_sql(t):
            if t in subqueries: return self.generate(subqueries[t])
            return f"SELECT * FROM {t}"
        if "UNION ALL" in table:
            new_parts = ["UNION ALL\n" + _item_sql(t) for t in op.tables]
            return table + "\n" + "\n".join(new_parts)
        first = f"SELECT * FROM {table}"
        rest = ["UNION ALL\n" + _item_sql(t) for t in op.tables]
        return first + "\n" + "\n".join(rest)

    def _render_bin(self, col, amount, unit):
        seconds_per_unit = {"d":86400,"h":3600,"m":60,"s":1}
        if unit in ("d","h") or (unit == "m" and amount == 1) or unit == "s":
            trunc = _DATE_TRUNC_UNIT.get(unit, unit)
            return f"DATE_TRUNC('{trunc}', {col})"
        total_seconds = amount * seconds_per_unit.get(unit, 1)
        return f"TIMESTAMP_SECONDS(FLOOR(UNIX_TIMESTAMP({col}) / {total_seconds}) * {total_seconds})"

    def _expr(self, expr) -> str:
        if isinstance(expr, ColumnRef):
            if getattr(self, "_scalar_bindings", None) and expr.name in self._scalar_bindings:
                return self._expr(self._scalar_bindings[expr.name])
            return expr.name
        if isinstance(expr, StringLit): return f"'{expr.value}'"
        if isinstance(expr, IntLit): return str(expr.value)
        if isinstance(expr, FloatLit): return str(expr.value)
        if isinstance(expr, BoolLit): return "TRUE" if expr.value else "FALSE"
        if isinstance(expr, AgoExpr):
            unit = _INTERVAL_UNIT.get(expr.unit, expr.unit)
            return f"CURRENT_TIMESTAMP - INTERVAL '{expr.amount} {unit}'"
        if isinstance(expr, BinExpr):
            return self._render_bin(self._expr(expr.col), expr.amount, expr.unit)
        if isinstance(expr, BinaryOp):
            return f"({self._expr(expr.left)} {expr.op} {self._expr(expr.right)})"
        if isinstance(expr, Comparison):
            if expr.op == "=~":
                return f"(LOWER({self._expr(expr.left)}) = LOWER({self._expr(expr.right)}))"
            op_map = {"==":"=","=~":"=","!=":"!=","<":"<",">":">","<=":"<=",">=":">="}
            return f"({self._expr(expr.left)} {op_map.get(expr.op, expr.op)} {self._expr(expr.right)})"
        if isinstance(expr, FuncCall): return self._func_call(expr)
        if isinstance(expr, DatetimeLit):
            inner = expr.raw.replace("datetime(","").rstrip(")").strip("'\"")
            return f"TIMESTAMP '{inner}'"
        if isinstance(expr, str): return expr
        if isinstance(expr, IffExpr):
            branches = []
            curr = expr
            while isinstance(curr, IffExpr):
                cond = self._bool_expr(curr.condition)
                true_v = self._expr(curr.true_val)
                branches.append(f"WHEN {cond} THEN {true_v}")
                curr = curr.false_val
            return f"CASE {' '.join(branches)} ELSE {self._expr(curr)} END"
        raise NotImplementedError(f"Unknown expr: {type(expr).__name__}")

    def _func_call(self, expr: FuncCall) -> str:
        name = expr.name.lower()
        if name == "iff" and len(expr.args) == 3:
            return self._render_iff_func(expr)
        args = [self._expr(a) for a in expr.args]
        kql_to_spark = {
            "tostring": lambda a: f"CAST({a[0]} AS STRING)",
            "toint": lambda a: f"CAST({a[0]} AS INT)",
            "tolong": lambda a: f"CAST({a[0]} AS BIGINT)",
            "todouble": lambda a: f"CAST({a[0]} AS DOUBLE)",
            "strlen": lambda a: f"LENGTH({a[0]})",
            "tolower": lambda a: f"LOWER({a[0]})",
            "toupper": lambda a: f"UPPER({a[0]})",
            "trim": lambda a: (f"TRIM(BOTH {a[0]} FROM {a[1]})" if len(a) >= 2 else f"TRIM({a[0]})"),
            "ltrim": lambda a: (f"LTRIM({a[1]})" if len(a) >= 2 else f"LTRIM({a[0]})"),
            "rtrim": lambda a: (f"RTRIM({a[1]})" if len(a) >= 2 else f"RTRIM({a[0]})"),
            "replace": lambda a: f"REPLACE({a[0]}, {a[1]}, {a[2]})",
            "substring": lambda a: f"SUBSTRING({a[0]}, {a[1]}, {a[2]})",
            "strcat": lambda a: " || ".join(a),
            "now": lambda a: "CURRENT_TIMESTAMP",
            "startofday": lambda a: f"DATE_TRUNC('day', {a[0]})",
            "startofhour": lambda a: f"DATE_TRUNC('hour', {a[0]})",
            "startofmonth": lambda a: f"DATE_TRUNC('month', {a[0]})",
            "startofyear": lambda a: f"DATE_TRUNC('year', {a[0]})",
            "format_datetime": lambda a: f"DATE_FORMAT({a[0]}, {a[1]})",
            "dayofweek": lambda a: f"DAYOFWEEK({a[0]})",
            "hourofday": lambda a: f"HOUR({a[0]})",
            "coalesce": lambda a: f"COALESCE({', '.join(a)})",
            "split": lambda a: f"split({a[0]}, {a[1]})",
            "strcat_delim": lambda a: f"concat_ws({a[0]}, {', '.join(a[1:])})",
            "array_length": lambda a: f"size({a[0]})",
            "bin_auto": lambda a: self._render_bin(a[0], 1, "d"),
            "case": lambda a: self._render_case(a),
            "parse_json": lambda a: a[0],
            "parse_json_path": lambda a: f"get_json_object({a[0]}, '$.{a[1].strip(chr(39)).strip(chr(34))}')",
            "ipv4_is_private": lambda a: self._render_ipv4_is_private(a[0]),
            "ipv4_is_in_range": lambda a: self._render_ipv4_in_range(a[0], a[1].strip(chr(39)).strip(chr(34))),
        }
        if name in kql_to_spark:
            return kql_to_spark[name](args)
        # Window functions: prev/next → LAG/LEAD, row_number/rank/dense_rank with OVER clause
        if name in ("prev", "next", "row_number", "rank", "dense_rank", "ntile", "percent_rank", "cume_dist"):
            return self._render_window_func_ast(name, args)
        args_str = ", ".join(args)
        return f"{name}({args_str})"

    def _render_ipv4_is_private(self, col_sql: str) -> str:
        """
        Expand ipv4_is_private into BETWEEN ranges for RFC 1918 private addresses.
        """
        ranges = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
        parts = []
        for cidr in ranges:
            net = ipaddress.IPv4Network(cidr)
            low = int(net.network_address)
            high = int(net.broadcast_address)
            parts.append(f"(CAST(CONV(HEX(INET_ATON({col_sql})), 16, 10) AS BIGINT) BETWEEN {low} AND {high})")
        return f"({' OR '.join(parts)})"

    def _render_ipv4_in_range(self, col_sql: str, cidr: str) -> str:
        """
        Expand ipv4_is_in_range into a BETWEEN check.
        """
        net = ipaddress.IPv4Network(cidr, strict=False)
        low = int(net.network_address)
        high = int(net.broadcast_address)
        return f"(CAST(CONV(HEX(INET_ATON({col_sql})), 16, 10) AS BIGINT) BETWEEN {low} AND {high})"

    def _render_window_func_ast(self, name: str, args: list[str]) -> str:
        """Render AST-level window functions with OVER clause using hint."""
        func_map = {
            "prev": "LAG",
            "next": "LEAD",
            "row_number": "ROW_NUMBER",
            "rank": "RANK",
            "dense_rank": "DENSE_RANK",
            "percent_rank": "PERCENT_RANK",
            "cume_dist": "CUME_DIST",
            "ntile": "NTILE"
        }
        sql_func = func_map.get(name, name.upper())
        if name in ("row_number", "rank", "dense_rank", "percent_rank", "cume_dist"):
            func_args_str = ""
        else:
            func_args_str = ", ".join(args)

        over_parts = []
        hint = getattr(self, "hint", None)
        ws = getattr(hint, "window_spec", None) if hint else None

        if ws and getattr(ws, "partition_by", None):
            pb_cols = [c for c in ws.partition_by if c]
            if pb_cols:
                over_parts.append(f"PARTITION BY {', '.join(pb_cols)}")

        if ws and getattr(ws, "order_by", None):
            ob_cols = [c for c in ws.order_by if c]
            if ob_cols:
                over_parts.append(f"ORDER BY {', '.join(ob_cols)}")
            else:
                over_parts.append("ORDER BY (SELECT NULL)")
        else:
            over_parts.append("ORDER BY (SELECT NULL)")

        over_clause = " ".join(over_parts)
        return f"{sql_func}({func_args_str}) OVER ({over_clause})"

    def _render_case(self, args):
        if len(args) < 3: return f"CASE WHEN {', '.join(args)} END"
        branches = [f"WHEN {args[i]} THEN {args[i+1]}" for i in range(0, len(args)-1, 2)]
        return f"CASE {' '.join(branches)} ELSE {args[-1]} END"

    def _render_iff_func(self, expr: FuncCall) -> str:
        branches = []
        curr = expr
        while isinstance(curr, FuncCall) and curr.name.lower() == "iff" and len(curr.args) == 3:
            cond = self._expr(curr.args[0])
            true_v = self._expr(curr.args[1])
            branches.append(f"WHEN {cond} THEN {true_v}")
            curr = curr.args[2]
        if isinstance(curr, IffExpr):
            while isinstance(curr, IffExpr):
                cond = self._bool_expr(curr.condition)
                true_v = self._expr(curr.true_val)
                branches.append(f"WHEN {cond} THEN {true_v}")
                curr = curr.false_val
            default_val = self._expr(curr)
        else:
            default_val = self._expr(curr)
        return f"CASE {' '.join(branches)} ELSE {default_val} END"

    def _bool_expr(self, expr) -> str:
        if isinstance(expr, Comparison):
            left = self._expr(expr.left); right = self._expr(expr.right)
            is_right_true = (
                (isinstance(expr.right, BoolLit) and expr.right.value is True) or
                (isinstance(expr.right, ColumnRef) and expr.right.name.lower() == "true")
            )
            if expr.op == "==" and is_right_true and isinstance(expr.left, FuncCall):
                return left
            if expr.op == "=~": return f"LOWER({left}) = LOWER({right})"
            op = _COMP_OP_MAP.get(expr.op, expr.op)
            return f"{left} {op} {right}"
        if isinstance(expr, InExpr):
            col = self._expr(expr.col); not_kw = "NOT " if expr.negated else ""
            if getattr(expr, "case_insensitive", False):
                col = f"LOWER({col})"
                values = ", ".join(f"LOWER({self._expr(v)})" for v in expr.values)
            else:
                values = ", ".join(self._expr(v) for v in expr.values)
            return f"{col} {not_kw}IN ({values})"
        if isinstance(expr, SubqueryInExpr):
            col = self._expr(expr.col); not_kw = "NOT " if expr.negated else ""
            inner_sql = self.generate(expr.subquery)
            if getattr(expr, "case_insensitive", False):
                return f"LOWER({col}) {not_kw}IN (SELECT LOWER(x) FROM ({inner_sql}) AS _ci_sub(x))"
            return f"{col} {not_kw}IN ({inner_sql})"
        if isinstance(expr, StringOp):
            col = self._expr(expr.col)
            op_map = {
                "has": f"{col} RLIKE '(?i)\\\\b{expr.value}\\\\b'",
                "contains": f"{col} LIKE '%{expr.value}%'",
                "startswith": f"{col} LIKE '{expr.value}%'",
                "endswith": f"{col} LIKE '%{expr.value}'",
                "matches regex": f"regexp_like({col}, '{expr.value}')",
            }
            return op_map.get(expr.op, f"{col} LIKE '%{expr.value}%'")
        if isinstance(expr, NullCheck):
            col = self._expr(expr.col)
            return f"{col} IS NULL" if expr.is_null else f"{col} IS NOT NULL"
        if isinstance(expr, LogicalOp):
            left = self._bool_expr(expr.left); right = self._bool_expr(expr.right)
            return f"({left} {expr.op.upper()} {right})"
        if isinstance(expr, Negation):
            return f"NOT ({self._bool_expr(expr.expr)})"
        if isinstance(expr, HasAnyExpr):
            col = self._expr(expr.col)
            parts = []
            for v in expr.values:
                val_str = v.value if isinstance(v, StringLit) else self._expr(v).strip("'\"")
                parts.append(f"{col} RLIKE '(?i)\\\\b{val_str}\\\\b'")
            return f"({' OR '.join(parts)})"
        raise NotImplementedError(f"Unknown bool expr: {type(expr).__name__}")
