"""
verify.py — DuckDB Local Execution Verification Backend
========================================================
Phase 4D. Positions DuckDB explicitly as an in-memory verification engine.
Runs compiled queries locally against reference pandas/pyarrow DataFrames to check schema/row counts.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any

try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False

from .parser import parse
from .ir import to_semantic_ir


@dataclass(slots=True)
class VerificationResult:
    is_matching: bool
    row_count_match: bool
    schema_match: bool
    value_match: bool
    details: dict[str, Any]


def verify(kql_query: str, reference_df: Any) -> VerificationResult:
    """
    Runs the compiled DuckDB target SQL locally against a reference DataFrame to check consistency.
    """
    if not HAS_DUCKDB:
        raise ImportError("DuckDB is not installed. Run 'pip install duckdb' to use the verification backend.")

    from .__init__ import translate

    # 1. Compile query straight to a lightweight DuckDB SQL string
    duckdb_sql = translate(kql_query, target="duckdb")
    
    # 2. Extract base table name from IR to register the DataFrame in-memory
    ast_tree = parse(kql_query)
    ir_query = to_semantic_ir(ast_tree)
    base_table = ir_query.source_table

    # 3. Execute locally against the provided pandas/pyarrow memory reference
    con = duckdb.connect(database=":memory:")
    con.register(base_table, reference_df)
    
    candidate_df = con.execute(duckdb_sql).df()
    
    # 4. Check core compliance points
    schema_match = list(candidate_df.columns) == list(reference_df.columns)
    row_count_match = len(candidate_df) == len(reference_df)
    
    is_matching = schema_match and row_count_match
    
    return VerificationResult(
        is_matching=is_matching,
        row_count_match=row_count_match,
        schema_match=schema_match,
        value_match=True,  # Expanded during Phase 4E audits
        details={"columns": list(candidate_df.columns), "rows": len(candidate_df)}
    )
