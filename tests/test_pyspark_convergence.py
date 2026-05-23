import json
import re
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from kqlbridge.parser import parse
from kqlbridge.generators.pyspark import PySparkGenerator
from kqlbridge.ir import to_semantic_ir
from kqlbridge.ir.emitters.pyspark_ir import IRPySparkGenerator

TIER3_FILE = Path(__file__).parent / "tier3_queries.json"

# ─── Python Code Normalizer ───────────────────────────────────────────────────

def normalize_python(code: str) -> str:
    """
    Collapses formatting and quotes for Python code strings.
    """
    # Remove comments
    code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
    # Collapse all whitespace
    code = re.sub(r'\s+', ' ', code.strip())
    # Lowercase
    code = code.lower()
    # Normalize double quotes to single quotes
    code = re.sub(r'"([^"]*)"', lambda m: f"'{m.group(1)}'", code)
    # Normalize single-quoted escape quotes
    code = code.replace("\\'", "'")
    # Collapse again
    code = re.sub(r'\s+', ' ', code).strip()
    return code

# ─── Load queries ─────────────────────────────────────────────────────────────

def _load_tier3() -> list[dict]:
    if not TIER3_FILE.exists():
        return []
    return json.loads(TIER3_FILE.read_text(encoding="utf-8"))

TIER3_QUERIES = _load_tier3()

def assert_pyspark_converges(q_id: str, kql: str) -> None:
    """
    Assert that AST PySpark generator and IR PySpark generator outputs converge identically.
    """
    try:
        ast = parse(kql)
    except Exception as e:
        pytest.fail(f"[{q_id}] Parse failure: {e}\nKQL: {kql!r}")

    try:
        oracle_code = PySparkGenerator().generate(ast)
    except Exception as e:
        pytest.fail(f"[{q_id}] Oracle generation failure: {e}\nKQL: {kql!r}")

    try:
        ir = to_semantic_ir(ast, validate=True)
    except Exception as e:
        pytest.fail(f"[{q_id}] IR transformation failure: {e}\nKQL: {kql!r}")

    try:
        candidate_code = IRPySparkGenerator().emit(ir)
    except NotImplementedError as e:
        pytest.fail(
            f"[{q_id}] IR emitter missing primitive: {e}\n"
            f"KQL: {kql!r}\n"
            f"Add handling for this node type in pyspark_ir.py"
        )
    except Exception as e:
        pytest.fail(f"[{q_id}] IR emitter failure: {e}\nKQL: {kql!r}")

    oracle_norm = normalize_python(oracle_code)
    candidate_norm = normalize_python(candidate_code)

    assert oracle_norm == candidate_norm, (
        f"\n[{q_id}] PySpark Convergence MISMATCH\n"
        f"KQL:       {kql!r}\n"
        f"ORACLE:    {oracle_code}\n"
        f"CANDIDATE: {candidate_code}\n"
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
def test_pyspark_baseline_convergence(case):
    assert_pyspark_converges(case["id"], case["kql"])
