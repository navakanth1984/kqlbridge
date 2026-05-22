"""
ir/emitters/tsql_ir.py — IR-Driven T-SQL Emitter
=================================================
Phase 3C. Reads a SemanticQuery IR envelope and produces T-SQL (SQL Server).

Design (mirrors spark_ir.py pattern):
  - Inherits TSQLGenerator for ALL expression/clause rendering.
  - Overrides ONLY the orchestration layer (_emit_body).
  - Reads item.alias directly — same alias contract as spark_ir.py.

T-SQL dialect differences from Spark SQL:
  - Column identifiers: [alias] brackets instead of bare names
  - LIMIT → TOP N (placed after SELECT, not at end)
  - COUNT(DISTINCT x) → COUNT(DISTINCT x) (same)
  - Date functions: DATETRUNC, DATEDIFF, DATEADD (different signatures)
  - String functions: CHARINDEX instead of LOCATE, etc.
  - UNION ALL subquery wrapping: same as Spark

Convergence gate (Phase 3C):
  tests/test_tsql_convergence.py — same harness pattern as Spark Tier 1/2/3.
  Target: 353/353 before translate(target='tsql') switches to IR path.

Status: SCAFFOLD — not yet convergence-tested.
"""

from __future__ import annotations

from typing import List, Optional

from ..nodes import (
    SemanticQuery, SemanticFilter, SemanticProjection, ProjectionItem,
    SemanticAggregate, AggregateItem, SemanticJoin, SemanticUnion,
)


class IRTSQLGenerator:
    """
    Emits T-SQL by walking a SemanticQuery IR envelope.

    Phase 3C scaffold. Inherits TSQLGenerator once that class is refactored
    to expose _assemble() as a separate method (same refactor as spark_sql.py
    Phase 3A). Until then, this class operates standalone.

    Usage::

        from kqlbridge.ir import to_semantic_ir
        from kqlbridge.ir.emitters.tsql_ir import IRTSQLGenerator
        from kqlbridge.parser import parse

        ir = to_semantic_ir(parse("T | where x == 1 | project x"))
        sql = IRTSQLGenerator().emit(ir)
    """

    def emit(self, ir: SemanticQuery) -> str:
        """
        Main entrypoint. CTEs (let bindings) first, then body.
        T-SQL uses standard WITH ... AS (...) CTE syntax.
        """
        ctes = []
        for cte_name, cte_ir in ir.ctes.items():
            sub_sql = self._emit_body(cte_ir)
            ctes.append(f"{cte_name} AS (\n  {sub_sql}\n)")

        body = self._emit_body(ir)

        if ctes:
            return f"WITH {', '.join(ctes)}\n{body}"
        return body

    def _emit_body(self, ir: SemanticQuery) -> str:
        """
        Walk IR steps. Same structure as IRSparkSQLGenerator._emit_body()
        with T-SQL dialect overrides applied at assembly time.

        TODO (Phase 3C):
          - Inherit from TSQLGenerator once _assemble() is extracted
          - Override only: _render_bin(), _func_call() for TSQL date functions
          - Expression rendering is 80% identical to Spark — delta is small
        """
        raise NotImplementedError(
            "IRTSQLGenerator._emit_body() is a Phase 3C deliverable.\n"
            "Current path: TSQLGenerator (AST-based) via translate(use_ir=False).\n"
            "Prerequisite: refactor TSQLGenerator to expose _assemble() as a "
            "separate method (same pattern as spark_sql.py Phase 3A refactor)."
        )

    # ─── T-SQL dialect overrides (stub) ───────────────────────────────────

    def _bracket(self, name: str) -> str:
        """Wrap identifier in T-SQL brackets: col → [col]"""
        return f"[{name}]"

    def _top_clause(self, limit: int) -> str:
        """T-SQL uses TOP N in SELECT position, not LIMIT at end."""
        return f"TOP {limit}"

    def _render_bin(self, col: str, amount: int, unit: str) -> str:
        """
        T-SQL bin() equivalent using DATETRUNC (SQL Server 2022+)
        or DATEDIFF/DATEADD pattern for older versions.
        """
        # Modern SQL Server 2022+: DATETRUNC(hour, col)
        unit_map = {"d": "day", "h": "hour", "m": "minute", "s": "second"}
        trunc_unit = unit_map.get(unit)
        if trunc_unit and amount == 1:
            return f"DATETRUNC({trunc_unit}, {col})"
        # Fallback: DATEDIFF/DATEADD pattern
        seconds_map = {"d": 86400, "h": 3600, "m": 60, "s": 1}
        total_seconds = amount * seconds_map.get(unit, 1)
        return (
            f"DATEADD(SECOND, "
            f"(DATEDIFF(SECOND, '1970-01-01', {col}) / {total_seconds}) * {total_seconds}, "
            f"'1970-01-01')"
        )
