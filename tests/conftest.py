"""
tests/conftest.py — KQLBridge Phase 3B pytest session hooks
============================================================
Automatically writes convergence_report.json after any pytest session
that touches test_tier3_convergence.py or test_phase3b_gate.py.

This means every `py -m pytest` run that includes Tier 3 tests keeps
the report artifact up to date — no manual `py tests/convergence_report.py`
needed during active repair cycles.

Also defines the hardened normalize_sql() fixture available to all test files.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ─── Hardened normalize_sql — Category A drift coverage ──────────────────────

def normalize_sql(sql: str) -> str:
    """
    Canonical SQL normalizer shared across all convergence test files.

    Category A (Formatting Drift) coverage:
      - Whitespace / newlines → single space
      - Keyword case → lowercase
      - <> → != (not-equal normalization)
      - Paren spacing: '( ' → '(' and ' )' → ')'
      - Comma spacing → ', '
      - Operator spacing → ' = ', ' != ', ' > ', ' < '
      - UNION ALL / JOIN keyword spacing
      - Trailing semicolons stripped
      - Repeated DISTINCT keyword collapsed
      - AS keyword spacing: 'col  AS  alias' → 'col AS alias'

    Category B and C (semantic gaps) are NOT masked by this normalizer —
    those require fixes in spark_ir.py or transformer.py.
    """
    # Strip trailing semicolons
    sql = sql.rstrip(";").strip()

    # Collapse all whitespace including newlines
    sql = re.sub(r'\s+', ' ', sql).strip()

    # Normalize not-equal
    sql = sql.replace('<>', '!=')

    # Lowercase everything (both sides go through same normalizer)
    sql = sql.lower()

    # Paren spacing
    sql = re.sub(r'\(\s+', '(', sql)
    sql = re.sub(r'\s+\)', ')', sql)

    # Comma spacing → always ', '
    sql = re.sub(r'\s*,\s*', ', ', sql)

    # Operator spacing — order matters (handle != before =)
    sql = re.sub(r'\s*!=\s*', ' != ', sql)
    sql = re.sub(r'\s*>=\s*', ' >= ', sql)
    sql = re.sub(r'\s*<=\s*', ' <= ', sql)
    sql = re.sub(r'\s*<\s*(?!=)', ' < ', sql)     # not part of !=, <=
    sql = re.sub(r'\s*>\s*(?!=)', ' > ', sql)     # not part of >=
    sql = re.sub(r'\s*=\s*(?![=>])', ' = ', sql)  # not part of >=, <=, !=

    # AS keyword spacing
    sql = re.sub(r'\s+as\s+', ' as ', sql)

    # UNION ALL / JOIN keyword normalization
    sql = re.sub(r'\bunion\s+all\b', 'union all', sql)
    sql = re.sub(r'\binner\s+join\b', 'inner join', sql)
    sql = re.sub(r'\bleft\s+outer\s+join\b', 'left outer join', sql)
    sql = re.sub(r'\bright\s+outer\s+join\b', 'right outer join', sql)
    sql = re.sub(r'\bfull\s+outer\s+join\b', 'full outer join', sql)

    # GROUP BY / ORDER BY keyword normalization
    sql = re.sub(r'\bgroup\s+by\b', 'group by', sql)
    sql = re.sub(r'\border\s+by\b', 'order by', sql)

    # Collapse again after all substitutions
    sql = re.sub(r'\s+', ' ', sql).strip()

    return sql


@pytest.fixture
def sql_normalizer():
    """Pytest fixture exposing the canonical SQL normalizer to any test."""
    return normalize_sql


@pytest.fixture(autouse=True)
def sandbox_mlm_agent():
    """Autouse fixture to reset the global mlm_agent before and after each test."""
    from kqlbridge import mlm_agent
    mlm_agent.clear()
    yield
    mlm_agent.clear()


# ─── Session-end convergence report hook ─────────────────────────────────────

TIER3_TEST_FILES = {
    "test_tier3_convergence.py",
    "test_phase3b_gate.py",
}

_tier3_was_run = False


def pytest_collection_modifyitems(items):
    """Track whether any Tier 3 or gate tests were collected."""
    global _tier3_was_run
    for item in items:
        if any(tf in str(item.fspath) for tf in TIER3_TEST_FILES):
            _tier3_was_run = True
            break


def pytest_sessionfinish(session, exitstatus):
    """
    After any session that ran Tier 3 tests, regenerate convergence_report.json.
    Runs silently — does not affect exit code.
    """
    if not _tier3_was_run:
        return

    try:
        from tests.convergence_report import build_report
        report_path = Path(__file__).parent / "convergence_report.json"

        import json
        report = build_report(run_tier3=True)
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        gate = report["gate_status"]
        t3 = report["tier3"]
        if t3["total"] > 0:
            rate = t3["rate"]
            status = "✅ GATE PASSED" if gate["phase3b_complete"] else f"📊 {rate:.1f}%"
            print(f"\n  [convergence] Tier 3: {t3['passing']}/{t3['total']} — {status}")
            print(f"  [convergence] Report: {report_path.relative_to(Path.cwd())}")
    except Exception:
        # Never let hook errors affect test results
        pass
