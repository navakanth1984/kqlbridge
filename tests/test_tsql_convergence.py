import json
import re
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from kqlbridge.parser import parse
from kqlbridge.generators.tsql import TSQLGenerator
from kqlbridge.ir import to_semantic_ir
from kqlbridge.ir.emitters.tsql_ir import IRTSQLGenerator

TIER3_FILE = Path(__file__).parent / "tier3_queries.json"

# ─── SQL Normalizer ───────────────────────────────────────────────────────────

def normalize_sql(sql: str) -> str:
    """
    Collapse formatting differences while preserving semantic structure.
    """
    sql = re.sub(r'\s+', ' ', sql.strip())
    sql = sql.replace('<>', '!=')
    sql = sql.lower()
    sql = re.sub(r'\s*,\s*', ', ', sql)
    sql = re.sub(r'\s*=\s*', ' = ', sql)
    sql = re.sub(r'\s*!=\s*', ' != ', sql)
    sql = re.sub(r'\s+', ' ', sql).strip()
    return sql

# ─── Load queries ─────────────────────────────────────────────────────────────

def _load_tier3() -> list[dict]:
    if not TIER3_FILE.exists():
        return []
    return json.loads(TIER3_FILE.read_text(encoding="utf-8"))

TIER3_QUERIES = _load_tier3()

def assert_tsql_converges(q_id: str, kql: str) -> None:
    """
    Assert that AST TSQL generator and IR TSQL generator outputs converge identically.
    """
    try:
        ast = parse(kql)
    except Exception as e:
        pytest.fail(f"[{q_id}] Parse failure: {e}\nKQL: {kql!r}")

    try:
        oracle_sql = TSQLGenerator().generate(ast)
    except Exception as e:
        pytest.fail(f"[{q_id}] Oracle generation failure: {e}\nKQL: {kql!r}")

    try:
        ir = to_semantic_ir(ast, validate=True)
    except Exception as e:
        pytest.fail(f"[{q_id}] IR transformation failure: {e}\nKQL: {kql!r}")

    try:
        candidate_sql = IRTSQLGenerator().emit(ir)
    except NotImplementedError as e:
        pytest.fail(
            f"[{q_id}] IR emitter missing primitive: {e}\n"
            f"KQL: {kql!r}\n"
            f"Add handling for this node type in tsql_ir.py"
        )
    except Exception as e:
        pytest.fail(f"[{q_id}] IR emitter failure: {e}\nKQL: {kql!r}")

    oracle_norm = normalize_sql(oracle_sql)
    candidate_norm = normalize_sql(candidate_sql)

    assert oracle_norm == candidate_norm, (
        f"\n[{q_id}] T-SQL Convergence MISMATCH\n"
        f"KQL:       {kql!r}\n"
        f"ORACLE:    {oracle_sql}\n"
        f"CANDIDATE: {candidate_sql}\n"
        f"ORACLE_N:  {oracle_norm}\n"
        f"CANDID_N:  {candidate_norm}"
    )

# ─── Tests ────────────────────────────────────────────────────────────────────

def test_tier3_file_exists():
    assert TIER3_FILE.exists(), (
        f"Tier 3 query file not found: {TIER3_FILE}\n"
        f"Generate it with: py tests/extract_tier3.py"
    )

@pytest.mark.parametrize("case", TIER3_QUERIES)
def test_tsql_baseline_convergence(case):
    assert_tsql_converges(case["id"], case["kql"])
