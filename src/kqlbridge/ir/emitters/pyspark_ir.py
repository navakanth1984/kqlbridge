"""
ir/emitters/pyspark_ir.py — IR-Driven PySpark DataFrame Emitter
===============================================================
Phase 3C. Reads a SemanticQuery IR envelope and produces PySpark
DataFrame transformation chains instead of SQL strings.

Design differs fundamentally from spark_ir.py:
  - Output is a Python code string, not SQL.
  - Each IR step maps to a named DataFrame variable assignment.
  - Chained: df_step_0 → df_step_1 → df_step_2 → ... → df_result
  - Avoids nested subqueries — translates directly to DataFrame API calls.

Example output for "T | where x > 0 | summarize count() by region":
    df_step_0 = spark.table("T")
    df_step_1 = df_step_0.filter(F.col("x") > 0)
    df_step_2 = df_step_1.groupBy(F.col("region")).agg(F.count("*").alias("count_"))
    df_result = df_step_2

Convergence gate (Phase 3C):
  Different from Spark convergence — comparison is against PySparkGenerator output.
  tests/test_pyspark_convergence.py
  Target: 353/353 before translate(target='pyspark') switches to IR path.

Status: SCAFFOLD — not yet convergence-tested.
"""

from __future__ import annotations

from ..nodes import (
    SemanticQuery, SemanticFilter, SemanticProjection, ProjectionItem,
    SemanticAggregate, AggregateItem, SemanticJoin, SemanticUnion,
)


class IRPySparkGenerator:
    """
    Emits PySpark DataFrame code by walking a SemanticQuery IR envelope.

    Phase 3C scaffold. Unlike IRSparkSQLGenerator (which inherits from
    SparkSQLGenerator), this class is standalone — PySpark uses the
    DataFrame API, not SQL string assembly.

    Usage::

        from kqlbridge.ir import to_semantic_ir
        from kqlbridge.ir.emitters.pyspark_ir import IRPySparkGenerator
        from kqlbridge.parser import parse

        ir = to_semantic_ir(parse("T | where x > 0 | summarize count() by region"))
        code = IRPySparkGenerator().emit(ir)
        print(code)
        # df_step_0 = spark.table("T")
        # df_step_1 = df_step_0.filter(F.col("x") > 0)
        # df_step_2 = df_step_1.groupBy(...).agg(...)
        # df_result = df_step_2
    """

    def emit(self, ir: SemanticQuery) -> str:
        """
        Main entrypoint. Generates a Python code block.
        CTEs become named DataFrames, referenced inline.
        """
        lines: list[str] = ["import pyspark.sql.functions as F", ""]

        # CTE DataFrames (let bindings)
        for cte_name, cte_ir in ir.ctes.items():
            cte_lines = self._emit_steps(cte_ir, df_prefix=f"cte_{cte_name}")
            lines.extend(cte_lines)
            lines.append(f"{cte_name} = cte_{cte_name}_result")
            lines.append("")

        # Main body
        body_lines = self._emit_steps(ir, df_prefix="df")
        lines.extend(body_lines)

        return "\n".join(lines)

    def _emit_steps(self, ir: SemanticQuery, df_prefix: str) -> list[str]:
        """
        Walk IR steps and emit sequential DataFrame assignments.

        TODO (Phase 3C):
          Implement each step type as a DataFrame transformation.
          Expression rendering: _expr() and _bool_expr() produce
          pyspark.sql.functions calls rather than SQL strings.
        """
        raise NotImplementedError(
            "IRPySparkGenerator._emit_steps() is a Phase 3C deliverable.\n"
            "Current path: PySparkGenerator (AST-based) via translate(use_ir=False).\n"
            "Implementation plan:\n"
            "  1. SemanticFilter  → df.filter(F.expr(...))\n"
            "  2. SemanticProject → df.select(*cols)\n"
            "  3. SemanticAggregate → df.groupBy(*gb).agg(*aggs)\n"
            "  4. SemanticJoin    → df.join(right_df, on=cond, how=kind)\n"
            "  5. SemanticUnion   → df.unionAll(branch_df)\n"
            "  6. pipeline_state  → .orderBy(), .limit(), .distinct()"
        )

    # ─── Expression renderers (stub) ──────────────────────────────────────

    def _col(self, name: str) -> str:
        """F.col('name')"""
        return f"F.col({name!r})"

    def _lit(self, value: object) -> str:
        """F.lit(value)"""
        return f"F.lit({value!r})"

    def _agg(self, item: AggregateItem) -> str:
        """
        Render a single AggregateItem as a PySpark agg expression.
        Example: AggregateItem(function_name='count', alias='total')
                 → F.count('*').alias('total')
        """
        func_map = {
            "count":   lambda args: "F.count('*')" if not args else f"F.count({args[0]})",
            "sum":     lambda args: f"F.sum({args[0]})",
            "avg":     lambda args: f"F.avg({args[0]})",
            "min":     lambda args: f"F.min({args[0]})",
            "max":     lambda args: f"F.max({args[0]})",
            "dcount":  lambda args: f"F.countDistinct({args[0]})",
        }
        fn = func_map.get(item.function_name)
        if fn is None:
            raise NotImplementedError(
                f"PySpark agg function {item.function_name!r} not yet mapped"
            )
        args = [self._col(str(a)) for a in item.arguments]
        expr = fn(args)
        if item.alias:
            return f"{expr}.alias({item.alias!r})"
        return expr
