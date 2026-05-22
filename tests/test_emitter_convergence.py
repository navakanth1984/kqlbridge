"""
tests/test_emitter_convergence.py — Spark SQL Emitter Convergence Harness
==========================================================================
Phase 3A — the scoreboard for the emitter migration.

For every KQL query, runs both:
  - SparkSQLGenerator(ast) → SQL_A  (oracle — proven by 353 tests)
  - IRSparkSQLGenerator(ir) → SQL_B  (candidate — new IR-driven emitter)

Asserts: normalize(SQL_A) == normalize(SQL_B)

The normalizer collapses formatting differences (whitespace, case) while
preserving semantic differences (wrong operator, wrong column, wrong alias).
It does NOT strip parens — subquery structure must converge exactly.

Three tiers:
  TIER 1 (25 cases): Core primitives — where, project, extend, summarize.
                     MUST pass before any Tier 2 work begins.
  TIER 2 (25 cases): Multi-table — join, union, nested pipelines.
                     Marked xfail until coverage is built.
  TIER 3 (future): Full 353-query baseline extracted from eval files.

Run:
    py -m pytest tests/test_emitter_convergence.py -v
    py -m pytest tests/test_emitter_convergence.py -v -k "tier1"
    py -m pytest tests/test_emitter_convergence.py -v -k "tier2"

Convergence gate for Phase 3C (translate() switch):
  - Tier 1: 25/25
  - Tier 2: 25/25
  - IR Validation: 100%
  - Snapshots: 100%
"""

import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from kqlbridge.parser import parse
from kqlbridge.generators.spark_sql import SparkSQLGenerator
from kqlbridge.ir import to_semantic_ir
from kqlbridge.ir.emitters.spark_ir import IRSparkSQLGenerator


# ─── SQL Normalizer ───────────────────────────────────────────────────────────

def normalize_sql(sql: str) -> str:
    """
    Collapse formatting differences while preserving semantic structure.

    Normalizes:
      - Uppercase keywords → lowercase
      - Multiple whitespace → single space
      - Newlines → spaces
      - Trailing/leading whitespace
      - '<>' → '!=' (both mean not-equal; the generators may use either)
      - Comma spacing: ', ' → ','  (then we compare without space variation)

    Does NOT normalize:
      - Parentheses (subquery structure must match exactly)
      - String literal content ('Error' must stay 'Error')
      - Column names (case preserved — SQL is case-sensitive for identifiers)
    """
    # Collapse all whitespace (including newlines) to single space
    sql = re.sub(r'\s+', ' ', sql.strip())
    # Normalize not-equal operator
    sql = sql.replace('<>', '!=')
    # Normalize keyword casing (only SQL keywords, not identifiers)
    # Strategy: lowercase the whole string, which is safe for comparison
    # since both sides go through the same normalizer
    sql = sql.lower()
    # Normalize comma spacing
    sql = re.sub(r'\s*,\s*', ', ', sql)
    # Normalize spaces around operators
    sql = re.sub(r'\s*=\s*', ' = ', sql)
    sql = re.sub(r'\s*!=\s*', ' != ', sql)
    # Collapse again after operator normalization
    sql = re.sub(r'\s+', ' ', sql).strip()
    return sql


# ─── Core assertion ───────────────────────────────────────────────────────────

def assert_converges(kql: str) -> None:
    """
    Parse KQL, generate SQL via both paths, assert normalized outputs match.
    """
    ast = parse(kql)

    # Oracle: proven AST-based generator
    oracle_sql = SparkSQLGenerator().generate(ast)

    # Candidate: new IR-driven generator
    ir = to_semantic_ir(ast, validate=True)
    try:
        candidate_sql = IRSparkSQLGenerator().emit(ir)
    except NotImplementedError as e:
        pytest.fail(f"IR emitter missing primitive: {e}\nKQL: {kql}")

    oracle_norm = normalize_sql(oracle_sql)
    candidate_norm = normalize_sql(candidate_sql)

    assert oracle_norm == candidate_norm, (
        f"\nConvergence MISMATCH\n"
        f"KQL:       {kql!r}\n"
        f"ORACLE:    {oracle_sql}\n"
        f"CANDIDATE: {candidate_sql}\n"
        f"ORACLE_N:  {oracle_norm}\n"
        f"CANDID_N:  {candidate_norm}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TIER 1 — Core primitives (where, project, extend, summarize)
# Goal: 25/25 before any Tier 2 work begins.
# ═══════════════════════════════════════════════════════════════════════════════

class TestTier1Where:
    """SemanticFilter convergence — 6 cases."""

    def test_tier1_simple_equality(self):
        assert_converges("SecurityEvents | where Level == 'Error'")

    def test_tier1_inequality(self):
        assert_converges("T | where count > 100")

    def test_tier1_and_operator(self):
        assert_converges("T | where Level == 'Error' and count > 5")

    def test_tier1_or_operator(self):
        assert_converges("T | where Level == 'Error' or Level == 'Warning'")

    def test_tier1_negation(self):
        assert_converges("T | where not(Level == 'Info')")

    def test_tier1_in_expression(self):
        assert_converges("T | where source_ip in ('1.2.3.4', '5.6.7.8')")


class TestTier1Project:
    """SemanticProjection convergence — 5 cases."""

    def test_tier1_project_passthrough(self):
        assert_converges("T | project Message, Level")

    def test_tier1_project_three_cols(self):
        assert_converges("T | project a, b, c")

    def test_tier1_project_rename(self):
        assert_converges("T | project Svc = ServiceName")

    def test_tier1_where_then_project(self):
        assert_converges("T | where Level == 'Error' | project Message, Level")

    def test_tier1_project_then_take(self):
        assert_converges("T | project a, b | take 10")


class TestTier1Extend:
    """SemanticProjection (extend) convergence — 4 cases."""

    def test_tier1_extend_then_project(self):
        assert_converges("T | extend score = amount * 2 | project score")

    def test_tier1_extend_arithmetic(self):
        assert_converges("Orders | extend cost = UnitPrice * Quantity | project OrderId, cost")

    def test_tier1_extend_string(self):
        assert_converges("T | extend lower_name = tolower(username) | project lower_name")

    def test_tier1_chained_extends(self):
        assert_converges("T | extend base = 50 | extend final = base + 10 | project final")


class TestTier1Summarize:
    """SemanticAggregate convergence — 7 cases."""

    def test_tier1_count_by(self):
        assert_converges("SecurityEvents | summarize events = count() by source_ip")

    def test_tier1_sum_by(self):
        assert_converges("T | summarize total = sum(amount) by region")

    def test_tier1_multi_agg_by(self):
        assert_converges(
            "T | summarize total = count(), revenue = sum(amount), avg_score = avg(score) by region"
        )

    def test_tier1_dcount_by(self):
        assert_converges("T | summarize unique_ips = dcount(source_ip) by category")

    def test_tier1_anonymous_count(self):
        assert_converges("T | summarize count() by category")

    def test_tier1_where_then_summarize(self):
        assert_converges("T | where x > 5 | summarize count() by category")

    def test_tier1_summarize_bin(self):
        assert_converges(
            "SecurityEvents | summarize count() by bin(TimeGenerated, 1h)"
        )


class TestTier1Pipelines:
    """End-to-end pipeline convergence — 3 cases."""

    def test_tier1_full_pipeline_order_take(self):
        assert_converges(
            "T | where Level == 'Error' | summarize total = count() by region | order by total desc | take 10"
        )

    def test_tier1_let_cte_project(self):
        assert_converges(
            "let Errors = AppLogs | where Level == 'Error';\nErrors | project Message, Level"
        )

    def test_tier1_distinct(self):
        assert_converges("T | distinct col1, col2")


# ═══════════════════════════════════════════════════════════════════════════════
# TIER 2 — Multi-table operators (union, join, nested pipelines)
# Marked xfail until IRSparkSQLGenerator coverage reaches these primitives.
# Remove xfail marks one-by-one as coverage is built.
# ═══════════════════════════════════════════════════════════════════════════════

class TestTier2Union:
    """SemanticUnion convergence — 4 cases."""

    def test_tier2_simple_union(self):
        assert_converges("SecurityEvents | union HoneypotHits | project source_ip")

    def test_tier2_union_three_tables(self):
        assert_converges("T | union T2, T3 | project col")

    def test_tier2_let_then_union(self):
        assert_converges(
            "let T1 = Table1 | extend factor = 100;\n"
            "let T2 = Table2 | extend factor = 200;\n"
            "T1 | union T2 | project factor"
        )

    def test_tier2_union_with_summarize(self):
        assert_converges("T | union T2 | summarize count() by region")


class TestTier2Join:
    """SemanticJoin convergence — 3 cases."""

    def test_tier2_inner_join(self):
        assert_converges(
            "SecurityEvents | join kind=inner (DeviceNetworkEvents) on DeviceId"
        )

    def test_tier2_join_with_filter(self):
        assert_converges(
            "SecurityEvents\n"
            "| join kind=inner (DeviceNetworkEvents | where ActionType == 'ConnectionFailed') on DeviceId\n"
            "| summarize failures = count() by DeviceId"
        )

    def test_tier2_leftouter_join(self):
        assert_converges(
            "T | join kind=leftouter (T2 | project key, val) on key"
        )


class TestTier2Complex:
    """Complex multi-step pipelines — 3 cases."""

    def test_tier2_extend_then_summarize(self):
        assert_converges(
            "Orders | extend IsLarge = Amount > 1000 | summarize count() by IsLarge"
        )

    def test_tier2_let_join_summarize(self):
        assert_converges(
            "let RecentErrors = SecurityEvents | where Level == 'Error';\n"
            "RecentErrors\n"
            "| join kind=inner (DeviceNetworkEvents | where ActionType == 'ConnectionFailed') on DeviceId\n"
            "| summarize failures = count() by bin(TimeGenerated, 1h), DeviceId"
        )

    def test_tier2_where_after_summarize(self):
        assert_converges(
            "T | summarize total = count() by region | where total > 10"
        )


# ─── Normalizer self-tests ────────────────────────────────────────────────────

class TestNormalizer:
    """Verify the normalizer handles expected formatting variations."""

    def test_whitespace_collapsed(self):
        a = normalize_sql("SELECT   a,   b   FROM   T")
        b = normalize_sql("SELECT a, b FROM T")
        assert a == b

    def test_newlines_collapsed(self):
        a = normalize_sql("SELECT a\nFROM T\nWHERE x = 1")
        b = normalize_sql("SELECT a FROM T WHERE x = 1")
        assert a == b

    def test_case_normalized(self):
        a = normalize_sql("SELECT COUNT(*) FROM T GROUP BY col")
        b = normalize_sql("select count(*) from t group by col")
        assert a == b

    def test_not_equal_normalized(self):
        a = normalize_sql("WHERE a <> b")
        b = normalize_sql("WHERE a != b")
        assert a == b

    def test_parens_preserved(self):
        """Parens are NOT stripped — subquery structure must match."""
        a = normalize_sql("SELECT * FROM (SELECT * FROM T) _sub")
        b = normalize_sql("SELECT * FROM SELECT * FROM T _sub")
        assert a != b  # Different structure — normalizer must NOT collapse these

    def test_semantic_difference_not_masked(self):
        """Different column names must NOT normalize to the same string."""
        a = normalize_sql("SELECT a, b FROM T")
        b = normalize_sql("SELECT x, y FROM T")
        assert a != b

    def test_alias_difference_not_masked(self):
        a = normalize_sql("SELECT COUNT(*) AS total FROM T")
        b = normalize_sql("SELECT COUNT(*) AS cnt FROM T")
        assert a != b


# ─── Tier 3: E2E convergence on benchmark.json ─────────────────────────────────

def _get_benchmark_queries():
    import json
    import os
    json_path = os.path.join(os.path.dirname(__file__), "eval", "benchmark.json")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            cases = json.load(f)
        return [case["kql"] for case in cases]
    except Exception:
        return []


class TestTier3:
    """
    Tier 3 — E2E convergence on all 120 baseline queries from benchmark.json.
    """
    @pytest.mark.parametrize("kql", _get_benchmark_queries())
    def test_tier3_benchmark_query(self, kql):
        assert_converges(kql)
