"""
ir/emitters/tsql_ir.py — IR-Driven T-SQL Emitter
=================================================
Reads a SemanticQuery IR envelope and produces T-SQL (SQL Server).

Design:
  - Inherits TSQLGenerator for ALL expression/clause rendering.
  - Inherits IRSparkSQLGenerator for the step walking orchestration (_emit_body).
  - Overrides T-SQL-specific expression mappings (dates, types, functions, has_any, booleans).
  - Implements versioned temporal binning dynamically based on sql_server_version.
"""

from __future__ import annotations
import re
from typing import List, Optional

from ..nodes import (
    SemanticQuery, SemanticFilter, SemanticProjection, ProjectionItem,
    SemanticAggregate, AggregateItem, SemanticJoin, SemanticUnion,
    SemanticExpression, SemanticColumnRef, SemanticLiteral, SemanticComparison,
    SemanticLogicalOp, SemanticFunctionCall, SemanticSubquery,
    SemanticIndexedAccess, SemanticPropertyAccess,
    SemanticUnaryOp, SemanticBinaryOp,
)
from ...ast_nodes import ColumnRef, BinExpr, FuncCall, WhereOp
from ...generators.tsql import TSQLGenerator, _TSQL_DATEADD_UNIT
from .spark_ir import IRSparkSQLGenerator


class IRTSQLGenerator(IRSparkSQLGenerator, TSQLGenerator):
    """
    Emits T-SQL (SQL Server) by walking a SemanticQuery IR envelope.
    Inherits from IRSparkSQLGenerator and TSQLGenerator to reuse query walking
    while applying T-SQL specific expression and structural overrides.
    """

    def __init__(self, hint=None, oracle_parity=False, options=None):
        # Initialize TSQLGenerator
        TSQLGenerator.__init__(self, hint=hint, oracle_parity=oracle_parity, options=options)
        # Store options locally
        from ...options import CompilerOptions
        self.options = options if options is not None else CompilerOptions(oracle_parity=oracle_parity)
        self.oracle_parity = self.options.oracle_parity

    def _render_bin(self, col: str, amount: int, unit: str) -> str:
        """
        T-SQL bin() equivalent using DATETRUNC (SQL Server 2022+)
        or legacy DATEDIFF/DATEADD pattern for older versions.
        """
        if self.options.sql_server_version >= 2022 and amount == 1:
            trunc_units = {
                "d": "day",
                "h": "hour",
                "m": "minute",
                "s": "second",
                "ms": "millisecond",
            }
            trunc_unit = trunc_units.get(unit, unit)
            return f"DATETRUNC({trunc_unit}, {col})"
        
        # Fallback to TSQLGenerator's DATEADD/DATEDIFF implementation
        return TSQLGenerator._render_bin(self, col, amount, unit)

    def _expr(self, expr) -> str:
        if isinstance(expr, SemanticColumnRef):
            if expr.name.lower() in ("true", "false"):
                return "1" if expr.name.lower() == "true" else "0"
            if getattr(self, "_scalar_bindings", None) and expr.name in self._scalar_bindings:
                return self._expr(self._scalar_bindings[expr.name])
            return expr.name

        elif isinstance(expr, SemanticLiteral):
            val = expr.value
            if isinstance(val, bool):
                return "1" if val else "0"
            if isinstance(val, (int, float)):
                return str(val)
            if isinstance(val, str):
                if val.startswith("datetime(") and val.endswith(")"):
                    inner = val[9:-1].strip("'\"")
                    return f"CAST('{inner}' AS DATETIME2)"
                return f"'{val}'"
            return str(val)

        elif isinstance(expr, SemanticFunctionCall):
            return self._func_call(expr)

        elif isinstance(expr, SemanticIndexedAccess):
            col_sql = self._expr(expr.expression)
            idx_sql = self._expr(expr.index).strip("'\"")
            return f"JSON_VALUE({col_sql}, '$[{idx_sql}]')"

        elif isinstance(expr, SemanticPropertyAccess):
            col_sql = self._expr(expr.expression)
            return f"JSON_VALUE({col_sql}, '$.{expr.property}')"

        elif isinstance(expr, SemanticUnaryOp):
            return f"({expr.operator}{self._expr(expr.expression)})"

        elif isinstance(expr, SemanticBinaryOp):
            return f"({self._expr(expr.left)} {expr.operator} {self._expr(expr.right)})"

        return IRSparkSQLGenerator._expr(self, expr)

    def _func_call(self, expr: SemanticFunctionCall) -> str:
        name = expr.name.lower()
        args = expr.arguments

        if name == "bin":
            col_sql = self._expr(args[0])
            val_str = args[1].value if isinstance(args[1], SemanticLiteral) else str(args[1])
            m = re.match(r"(\d+)([a-zA-Z]+)", val_str.strip())
            if m:
                amount = int(m.group(1))
                unit = m.group(2)
            else:
                amount = 1
                unit = "d"
            return self._render_bin(col_sql, amount, unit)

        elif name == "ago":
            val_str = args[0].value if isinstance(args[0], SemanticLiteral) else str(args[0])
            m = re.match(r"(\d+)([a-zA-Z]+)", val_str.strip())
            if m:
                amount = int(m.group(1))
                unit = m.group(2)
            else:
                amount = 1
                unit = "d"
            tsql_unit = _TSQL_DATEADD_UNIT.get(unit, unit)
            return f"DATEADD({tsql_unit}, -{amount}, GETDATE())"

        elif name == "datetime":
            val_str = args[0].value if isinstance(args[0], SemanticLiteral) else str(args[0])
            val_clean = str(val_str).strip("'\"")
            return f"CAST('{val_clean}' AS DATETIME2)"

        elif name == "datetime_add":
            unit_str = args[0].value if isinstance(args[0], SemanticLiteral) else str(args[0])
            unit_clean = str(unit_str).strip("'\"").lower()
            tsql_unit = _TSQL_DATEADD_UNIT.get(unit_clean, unit_clean)
            amount_sql = self._expr(args[1])
            dt_sql = self._expr(args[2])
            return f"DATEADD({tsql_unit}, {amount_sql}, {dt_sql})"

        elif name == "datetime_diff":
            unit_str = args[0].value if isinstance(args[0], SemanticLiteral) else str(args[0])
            unit_clean = str(unit_str).strip("'\"").lower()
            tsql_unit = _TSQL_DATEADD_UNIT.get(unit_clean, unit_clean)
            dt1_sql = self._expr(args[1])
            dt2_sql = self._expr(args[2])
            return f"DATEDIFF({tsql_unit}, {dt2_sql}, {dt1_sql})"

        elif name == "array_index_of":
            arr_sql = self._expr(args[0])
            val_sql = self._expr(args[1])
            return f"COALESCE((SELECT MIN(CAST([key] AS INT)) FROM OPENJSON({arr_sql}) WHERE [value] = {val_sql}), -1)"

        elif name == "." and len(args) == 2:
            left_sql = self._expr(args[0])
            right = args[1].value if isinstance(args[1], SemanticLiteral) else self._expr(args[1])
            field_name = str(right).strip("'\"")
            return f"JSON_VALUE({left_sql}, '$.{field_name}')"

        elif name == "parse_json_path":
            col_sql = self._expr(args[0])
            field = args[1].value if isinstance(args[1], SemanticLiteral) else str(args[1])
            field_clean = str(field).strip("'\"")
            return f"JSON_VALUE({col_sql}, '$.{field_clean}')"

        elif name == "tostring":
            return f"CAST({self._expr(args[0])} AS NVARCHAR(MAX))"

        elif name == "toint":
            return f"CAST({self._expr(args[0])} AS INT)"

        elif name == "tolong":
            return f"CAST({self._expr(args[0])} AS BIGINT)"

        elif name == "todouble":
            return f"CAST({self._expr(args[0])} AS FLOAT)"

        elif name == "has_any":
            col_sql = self._expr(args[0])
            parts = []
            for v in args[1:]:
                val_str = v.value if isinstance(v, SemanticLiteral) else self._expr(v).strip("'\"")
                parts.append(f"{col_sql} LIKE '%{val_str}%'")
            return f"({' OR '.join(parts)})"

        elif name == "ipv4_is_private":
            col_sql = self._expr(args[0])
            return self._render_ipv4_is_private([col_sql])

        elif name == "ipv4_is_in_range":
            col_sql = self._expr(args[0])
            range_str = args[1].value if isinstance(args[1], SemanticLiteral) else str(args[1])
            range_clean = str(range_str).strip("'\"")
            return self._render_ipv4_in_range([col_sql, f"'{range_clean}'"])

        elif name == "regex":
            col_sql = self._expr(args[0])
            val_sql = self._expr(args[1])
            return f"{col_sql} LIKE {val_sql}"

        elif name in ("has", "contains", "startswith", "endswith"):
            col_sql = self._expr(args[0])
            val_str = args[1].value if isinstance(args[1], SemanticLiteral) else self._expr(args[1])
            val_clean = str(val_str).strip("'\"").replace("@", "")
            if name == "startswith": return f"{col_sql} LIKE '{val_clean}%'"
            if name == "endswith": return f"{col_sql} LIKE '%{val_clean}'"
            if name == "contains": return f"{col_sql} LIKE '%{val_clean}%'"
            return f"{col_sql} LIKE '%{val_clean}%'"

        # Fallback to base IR Spark generator for common functions
        return IRSparkSQLGenerator._func_call(self, expr)


    def _bool_expr(self, expr, is_top_level: bool = False) -> str:
        if isinstance(expr, SemanticLiteral):
            if isinstance(expr.value, bool):
                return "1" if expr.value else "0"
            return str(expr.value)
        if isinstance(expr, SemanticColumnRef):
            if expr.name.lower() in ("true", "false"):
                return "1" if expr.name.lower() == "true" else "0"

        return IRSparkSQLGenerator._bool_expr(self, expr, is_top_level=is_top_level)
