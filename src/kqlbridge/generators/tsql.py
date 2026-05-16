"""
generators/tsql.py — KQL AST → T-SQL
=====================================
AGENT MODIFIABLE — v0.2 target (Fabric SQL Warehouse, Synapse Analytics).

Do NOT implement until KQLBridge v0.1 reaches 85% eval score.
Karpathy Principle 2: add this only when the primary target is complete.

Notes for v0.2 implementation:
- Shares ~80% of logic with SparkSQLGenerator
- Key differences from Spark SQL:
  - DATE_TRUNC → DATEADD(unit, DATEDIFF(unit, 0, col), 0)
  - CURRENT_TIMESTAMP - INTERVAL → DATEADD(unit, -amount, GETDATE())
  - UNION ALL → same
  - LIMIT n → TOP n (in SELECT clause, not end of query)
"""

from __future__ import annotations

from ..ast_nodes import KQLQuery


class TSQLGenerator:
    """
    Generates T-SQL from a KQLQuery AST.
    Stub — implement in v0.2 after SparkSQLGenerator reaches 85%.
    """

    def generate(self, query: KQLQuery) -> str:
        raise NotImplementedError(
            "T-SQL generator is not implemented in v0.1. "
            "Target: implement after SparkSQLGenerator reaches 85% eval score."
        )
