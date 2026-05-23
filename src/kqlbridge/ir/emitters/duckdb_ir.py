"""
ir/emitters/duckdb_ir.py — IR-Driven DuckDB SQL Emitter
=========================================================
Phase 4D. Emits DuckDB-compatible SQL by walking a SemanticQuery IR envelope.
Since DuckDB is highly compatible with standard ANSI/Spark SQL, we inherit
directly from IRSparkSQLGenerator to maintain complete parity and prevent code duplication.
"""

from __future__ import annotations
from .spark_ir import IRSparkSQLGenerator


class IRDuckDBGenerator(IRSparkSQLGenerator):
    """
    Emits DuckDB-compatible SQL from a SemanticQuery IR envelope.
    """
    def __init__(self, hint=None, oracle_parity=False, options=None):
        super().__init__(hint=hint, oracle_parity=oracle_parity, options=options)
        self.dialect = "duckdb"
