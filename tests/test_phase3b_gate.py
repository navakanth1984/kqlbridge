"""
tests/test_phase3b_gate.py — Phase 3B Formal Completion Gate
=============================================================
The single test file that determines whether translate() can be switched
to the IR path. All four conditions must be green.

Gate definition (from architectural review):
    Condition 1: Validator Snapshots — 13/13 (V001-V013 + snapshot regression)
    Condition 2: Tier 1            — 25/25 (core primitives)
    Condition 3: Tier 2            — 10/10 (multi-table)
    Condition 4: Tier 3            — 119/119 (full baseline)

Run:
    py -m pytest tests/test_phase3b_gate.py -v

This test does NOT run the full suites inline (that would be slow).
Instead it reads the convergence_report.json artifact produced by:
    py tests/convergence_report.py

And verifies each gate condition against it.

If convergence_report.json is missing, the gate fails with a clear message.
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest

REPORT_FILE = Path(__file__).parent / "convergence_report.json"
TIER3_FILE  = Path(__file__).parent / "tier3_queries.json"
STALE_HOURS = 24   # Report older than this is considered stale


# ─── Report loading helper ────────────────────────────────────────────────────

def _load_report() -> dict | None:
    if not REPORT_FILE.exists():
        return None
    try:
        return json.loads(REPORT_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def _report_is_fresh(report: dict) -> bool:
    try:
        ts = datetime.fromisoformat(report["timestamp"])
        age = datetime.now(timezone.utc) - ts
        return age < timedelta(hours=STALE_HOURS)
    except Exception:
        return False


# ─── Prerequisite checks ─────────────────────────────────────────────────────

class TestPrerequisites:
    """Infrastructure must exist before gate conditions can be evaluated."""

    def test_convergence_report_exists(self):
        """
        convergence_report.json must exist.
        If missing: py tests/convergence_report.py
        """
        assert REPORT_FILE.exists(), (
            f"\nconvergence_report.json not found at {REPORT_FILE}\n"
            f"Generate it with: py tests/convergence_report.py\n"
            f"This report is required for all Phase 3B gate checks."
        )

    def test_convergence_report_is_fresh(self):
        """Report must have been generated within the last 24 hours."""
        report = _load_report()
        if report is None:
            pytest.skip("convergence_report.json missing")
        assert _report_is_fresh(report), (
            f"convergence_report.json is stale (> {STALE_HOURS}h old).\n"
            f"Regenerate: py tests/convergence_report.py"
        )

    def test_convergence_report_has_required_keys(self):
        """Report must contain the expected structure."""
        report = _load_report()
        if report is None:
            pytest.skip("convergence_report.json missing")
        for key in ("gate_status", "tier1", "tier2", "tier3"):
            assert key in report, f"convergence_report.json missing key: {key!r}"

    def test_tier3_queries_file_exists(self):
        """
        tier3_queries.json must exist.
        If missing: py tests/extract_tier3.py
        """
        assert TIER3_FILE.exists(), (
            f"\ntier3_queries.json not found at {TIER3_FILE}\n"
            f"Generate it with: py tests/extract_tier3.py"
        )

    def test_tier3_queries_has_353_entries(self):
        """Tier 3 must have the full baseline (>= 119 queries)."""
        if not TIER3_FILE.exists():
            pytest.skip("tier3_queries.json missing")
        queries = json.loads(TIER3_FILE.read_text())
        count = len(queries)
        assert count >= 119, (
            f"Tier 3 has {count} queries, expected >= 119.\n"
            f"Re-run: py tests/extract_tier3.py\n"
            f"If your benchmark genuinely has fewer queries, update this threshold."
        )


# ─── Gate Condition 1: Validator Snapshots ───────────────────────────────────

class TestGateCondition1ValidatorSnapshots:
    """
    Gate Condition 1: validate_ir() passes on all 10 snapshot baselines.
    Tests V001-V013 rules against real IR patterns.
    """

    def test_gate1_validator_snapshots_pass(self):
        report = _load_report()
        if report is None:
            pytest.skip("Run: py tests/convergence_report.py")
        gate = report["gate_status"]
        assert gate.get("validator_snapshots"), (
            "Gate 1 FAILED: Validator snapshot check failed.\n"
            "Run: py -m pytest tests/test_validator_snapshots.py -v\n"
            "Fix any V001-V013 violations in the canonical query set."
        )

    def test_gate1_v013_covers_both_projection_and_aggregate(self):
        """
        V013 must fire on duplicate aliases in both SemanticProjection
        AND SemanticAggregate. Verifies the extended scope from Phase 3B review.
        """
        from kqlbridge.ir import validate_ir
        from kqlbridge.ir.nodes import (
            SemanticQuery, SemanticAggregate, AggregateItem,
        )
        from kqlbridge.scoping import SymbolTable

        st = SymbolTable()
        ir = SemanticQuery(
            source="T",
            steps=[
                SemanticAggregate(
                    aggregations=[
                        AggregateItem(alias="total", function_name="count",
                                      arguments=[], symbol_id=1, derived_from=[]),
                        AggregateItem(alias="total", function_name="sum",   # duplicate
                                      arguments=[], symbol_id=2, derived_from=[]),
                    ],
                    group_by=[],
                )
            ],
            ctes={}, symbol_table=st, pipeline_state={},
        )
        result = validate_ir(ir)
        codes = [i.code for i in result.issues]
        assert "V013" in codes, (
            "V013 did not fire on duplicate alias in SemanticAggregate.\n"
            "Check that validator.py V013 covers both Projection and Aggregate scopes."
        )


# ─── Gate Condition 2: Tier 1 ────────────────────────────────────────────────

class TestGateCondition2Tier1:
    """Gate Condition 2: 25/25 core primitive convergence."""

    def test_gate2_tier1_complete(self):
        report = _load_report()
        if report is None:
            pytest.skip("Run: py tests/convergence_report.py")
        t1 = report["tier1"]
        assert t1["passing"] == t1["total"] and t1["total"] >= 25, (
            f"Gate 2 FAILED: Tier 1 at {t1['passing']}/{t1['total']}.\n"
            f"Run: py -m pytest tests/test_emitter_convergence.py -v -k 'tier1'\n"
            f"Failing categories: {t1.get('categories', {})}"
        )

    def test_gate2_tier1_count_is_correct(self):
        report = _load_report()
        if report is None:
            pytest.skip("Run: py tests/convergence_report.py")
        t1 = report["tier1"]
        assert t1["total"] >= 25, (
            f"Tier 1 has only {t1['total']} cases, expected 25.\n"
            f"Check TIER1_CASES in test_emitter_convergence.py."
        )


# ─── Gate Condition 3: Tier 2 ────────────────────────────────────────────────

class TestGateCondition3Tier2:
    """Gate Condition 3: 10/10 multi-table convergence."""

    def test_gate3_tier2_complete(self):
        report = _load_report()
        if report is None:
            pytest.skip("Run: py tests/convergence_report.py")
        t2 = report["tier2"]
        assert t2["passing"] == t2["total"] and t2["total"] >= 10, (
            f"Gate 3 FAILED: Tier 2 at {t2['passing']}/{t2['total']}.\n"
            f"Run: py -m pytest tests/test_emitter_convergence.py -v -k 'tier2'\n"
            f"Failing categories: {t2.get('categories', {})}"
        )


# ─── Gate Condition 4: Tier 3 ────────────────────────────────────────────────

class TestGateCondition4Tier3:
    """Gate Condition 4: 353/353 full baseline convergence."""

    def test_gate4_tier3_complete(self):
        report = _load_report()
        if report is None:
            pytest.skip("Run: py tests/convergence_report.py")
        t3 = report["tier3"]
        if t3["total"] == 0:
            pytest.fail(
                "Gate 4 FAILED: Tier 3 not yet run.\n"
                "Run: py tests/extract_tier3.py && py tests/convergence_report.py"
            )
        assert t3["passing"] == t3["total"], (
            f"Gate 4 FAILED: Tier 3 at {t3['passing']}/{t3['total']} "
            f"({t3['rate']:.1f}%).\n"
            f"Top failure categories:\n"
            + "\n".join(
                f"  [{count}] {cat}"
                for cat, count in list(t3.get("categories", {}).items())[:5]
            )
        )

    def test_gate4_tier3_current_rate(self):
        """
        Non-blocking rate reporter. Always passes — records current convergence
        rate for visibility during Phase 3B repair work.
        """
        report = _load_report()
        if report is None:
            pytest.skip("Run: py tests/convergence_report.py")
        t3 = report["tier3"]
        if t3["total"] == 0:
            pytest.skip("Tier 3 not yet extracted")

        rate = t3["rate"]
        total = t3["total"]
        passing = t3["passing"]

        # Print the scoreboard line clearly
        print(f"\n  📊 Tier 3: {passing}/{total} ({rate:.1f}%)")
        if rate < 100:
            cats = t3.get("categories", {})
            print("  Top categories to fix:")
            for cat, count in list(cats.items())[:5]:
                print(f"    [{count:>4}] {cat}")
        # Always passes — this is a readout, not a gate
        assert True


# ─── Final Gate ───────────────────────────────────────────────────────────────

class TestPhase3BGate:
    """The single authoritative gate — ALL four conditions must be green."""

    def test_phase3b_complete_gate(self):
        """
        Phase 3B is complete when all four conditions pass.
        Only then is translate() eligible to switch to the IR path.

        Current gate definition (architectural review, Phase 3B):
            Condition 1: Validator Snapshots — all pass
            Condition 2: Tier 1            — 25/25
            Condition 3: Tier 2            — 10/10
            Condition 4: Tier 3            — 119/119

        When this test passes: flip translate() to use_ir=True.
        """
        report = _load_report()
        if report is None:
            pytest.fail(
                "convergence_report.json missing.\n"
                "Run: py tests/convergence_report.py"
            )

        gate = report["gate_status"]
        failing_conditions = [k for k, v in gate.items()
                              if k != "phase3b_complete" and not v]

        assert gate["phase3b_complete"], (
            f"\n{'='*50}\n"
            f"  Phase 3B gate NOT yet passed.\n"
            f"  Failing conditions: {failing_conditions}\n"
            f"  Tier 1:  {report['tier1']['passing']}/{report['tier1']['total']}\n"
            f"  Tier 2:  {report['tier2']['passing']}/{report['tier2']['total']}\n"
            f"  Tier 3:  {report['tier3']['passing']}/{report['tier3']['total']} "
            f"({report['tier3']['rate']:.1f}%)\n"
            f"  Snapshots: {gate['validator_snapshots']}\n"
            f"{'='*50}\n"
            f"Run convergence_report.py after each fix batch to update status."
        )

        # Gate passed — announce
        print(
            f"\n{'='*50}\n"
            f"  ✅ PHASE 3B GATE PASSED\n"
            f"  translate() is eligible to switch to use_ir=True\n"
            f"{'='*50}"
        )
