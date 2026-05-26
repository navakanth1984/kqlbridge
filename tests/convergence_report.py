"""
tests/convergence_report.py — Phase 3B Convergence Report Generator
====================================================================
Produces a machine-readable JSON artifact after every Tier 3 run.
Enables GitHub Actions trend tracking, release dashboards, and
regression detection across sessions.

Usage:
    py tests/convergence_report.py               # full report
    py tests/convergence_report.py --tier1       # tier1 only
    py tests/convergence_report.py --out path/to/report.json

Output: tests/convergence_report.json
    {
      "timestamp": "2026-05-22T14:30:00",
      "gate_status": {
        "validator_snapshots": true,
        "tier1": true,
        "tier2": true,
        "tier3": false,
        "phase3b_complete": false
      },
      "tier1":  {"total": 25,  "passing": 25,  "failing": 0,  "rate": 100.0},
      "tier2":  {"total": 10,  "passing": 10,  "failing": 0,  "rate": 100.0},
      "tier3":  {"total": 353, "passing": 281, "failing": 72, "rate": 79.6},
      "categories": {
        "NotImpl:StringOp": 41,
        "mismatch_at_join": 12,
        "mismatch_at_select": 9
      },
      "failing_ids": ["q0023", "q0047", ...]
    }

Also auto-run by conftest.py after every pytest session that touches
test_tier3_convergence.py.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

ROOT = Path(__file__).parent.parent
TIER3_FILE = Path(__file__).parent / "tier3_queries.json"
REPORT_FILE   = Path(__file__).parent / "convergence_report.json"
HISTORY_FILE  = Path(__file__).parent / "convergence_history.json"


# ─── SQL Normalizer (canonical — shared with test files) ─────────────────────

def normalize_sql(sql: str) -> str:
    sql = re.sub(r'\s+', ' ', sql.strip())
    sql = sql.replace('<>', '!=')
    sql = sql.lower()
    sql = re.sub(r'\s*,\s*', ', ', sql)
    sql = re.sub(r'\(\s+', '(', sql)
    sql = re.sub(r'\s+\)', ')', sql)
    sql = re.sub(r'\s*=\s*(?!=)', ' = ', sql)
    sql = re.sub(r'\s*!=\s*', ' != ', sql)
    sql = re.sub(r'\s+', ' ', sql).strip()
    return sql


# ─── Tier runners ─────────────────────────────────────────────────────────────

def _run_tier(cases: list[tuple[str, str]], label: str) -> dict:
    """Run a list of (id, kql) pairs through both generators. Returns tier stats."""
    from kqlbridge.parser import parse
    from kqlbridge.generators.spark_sql import SparkSQLGenerator
    from kqlbridge.ir import to_semantic_ir
    from kqlbridge.ir.emitters.spark_ir import IRSparkSQLGenerator

    passing = 0
    failing_ids: list[str] = []
    categories: dict[str, int] = {}

    for q_id, kql in cases:
        try:
            ast = parse(kql)
            oracle = normalize_sql(SparkSQLGenerator().generate(ast))
            ir = to_semantic_ir(ast)
            candidate = normalize_sql(IRSparkSQLGenerator().emit(ir))

            if oracle == candidate:
                passing += 1
            else:
                failing_ids.append(q_id)
                cat = _categorize_mismatch(oracle, candidate)
                categories[cat] = categories.get(cat, 0) + 1

        except NotImplementedError as e:
            failing_ids.append(q_id)
            cat = f"NotImpl:{type(e).__name__}:{str(e)[:40]}"
            categories[cat] = categories.get(cat, 0) + 1
        except Exception as e:
            failing_ids.append(q_id)
            cat = f"Error:{type(e).__name__}"
            categories[cat] = categories.get(cat, 0) + 1

    total = len(cases)
    failing = total - passing
    return {
        "total": total,
        "passing": passing,
        "failing": failing,
        "rate": round(passing / total * 100, 1) if total else 0.0,
        "categories": dict(sorted(categories.items(), key=lambda x: -x[1])),
        "failing_ids": failing_ids,
    }


def _categorize_mismatch(oracle: str, candidate: str) -> str:
    """Classify a SQL mismatch by the first structural difference."""
    oracle_tokens = oracle.split()
    cand_tokens = candidate.split()

    if len(oracle_tokens) != len(cand_tokens):
        return f"length_mismatch(oracle={len(oracle_tokens)},cand={len(cand_tokens)})"

    for i, (a, b) in enumerate(zip(oracle_tokens, cand_tokens)):
        if a != b:
            # Context window: 2 tokens before the diff
            context = "_".join(oracle_tokens[max(0, i-2):i+1])
            return f"mismatch_near:{context}"

    return "identical_after_normalize"  # shouldn't happen


# ─── Tier 1 and 2 cases (inline — same as test_emitter_convergence.py) ────────

def _get_tier1_cases() -> list[tuple[str, str]]:
    return [
        ("t1_where_eq", "SecurityEvents | where Level == 'Error'"),
        ("t1_where_and", "T | where Level == 'Error' and count > 5"),
        ("t1_where_or", "T | where Level == 'Error' or Level == 'Warning'"),
        ("t1_where_neg", "T | where not(Level == 'Info')"),
        ("t1_where_in", "T | where source_ip in ('1.2.3.4', '5.6.7.8')"),
        ("t1_where_func", "T | where isnotempty(name)"),
        ("t1_proj_pass", "T | project Message, Level"),
        ("t1_proj_three", "T | project a, b, c"),
        ("t1_proj_rename", "T | project Svc = ServiceName"),
        ("t1_where_proj", "T | where Level == 'Error' | project Message, Level"),
        ("t1_proj_take", "T | project a, b | take 10"),
        ("t1_ext_proj", "T | extend score = amount * 2 | project score"),
        ("t1_ext_arith", "Orders | extend cost = UnitPrice * Quantity | project OrderId, cost"),
        ("t1_ext_str", "T | extend lower_name = tolower(username) | project lower_name"),
        ("t1_ext_chain", "T | extend base = 50 | extend final = base + 10 | project final"),
        ("t1_sum_count", "SecurityEvents | summarize events = count() by source_ip"),
        ("t1_sum_sum", "T | summarize total = sum(amount) by region"),
        ("t1_sum_multi", "T | summarize total = count(), revenue = sum(amount), avg_score = avg(score) by region"),
        ("t1_sum_dcount", "T | summarize unique_ips = dcount(source_ip) by category"),
        ("t1_sum_anon", "T | summarize count() by category"),
        ("t1_where_sum", "T | where x > 5 | summarize count() by category"),
        ("t1_sum_bin", "SecurityEvents | summarize count() by bin(TimeGenerated, 1h)"),
        ("t1_full_pipe", "T | where Level == 'Error' | summarize total = count() by region | order by total desc | take 10"),
        ("t1_let_cte", "let Errors = AppLogs | where Level == 'Error';\nErrors | project Message, Level"),
        ("t1_distinct", "T | distinct col1, col2"),
    ]


def _get_tier2_cases() -> list[tuple[str, str]]:
    return [
        ("t2_union_bare", "SecurityEvents | union HoneypotHits | project source_ip"),
        ("t2_union_3", "T | union T2, T3 | project col"),
        ("t2_let_union", "let T1 = Table1 | extend factor = 100;\nlet T2 = Table2 | extend factor = 200;\nT1 | union T2 | project factor"),
        ("t2_union_sum", "T | union T2 | summarize count() by region"),
        ("t2_join_inner", "SecurityEvents | join kind=inner (DeviceNetworkEvents) on DeviceId"),
        ("t2_join_filter", "SecurityEvents | join kind=inner (DeviceNetworkEvents | where ActionType == 'ConnectionFailed') on DeviceId | summarize failures = count() by DeviceId"),
        ("t2_join_left", "T | join kind=leftouter (T2 | project key, val) on key"),
        ("t2_ext_sum", "Orders | extend IsLarge = Amount > 1000 | summarize count() by IsLarge"),
        ("t2_let_join_sum", "let RecentErrors = SecurityEvents | where Level == 'Error';\nRecentErrors | join kind=inner (DeviceNetworkEvents | where ActionType == 'ConnectionFailed') on DeviceId | summarize failures = count() by bin(TimeGenerated, 1h), DeviceId"),
        ("t2_where_after_sum", "T | summarize total = count() by region | where total > 10"),
    ]


# ─── Snapshot validator check ─────────────────────────────────────────────────

def _check_snapshot_gate() -> bool:
    """Returns True if all snapshot KQLs produce valid IR."""
    try:
        from kqlbridge.parser import parse
        from kqlbridge.ir import to_semantic_ir, validate_ir
        REGISTRY = [
            "SecurityEvents | where Level == 'Error'",
            "SecurityEvents | where Level == 'Error' | project Message, Level",
            "Orders | extend cost = UnitPrice * Quantity | project OrderId, cost",
            "SecurityEvents | summarize events = count() by source_ip",
            "T | summarize total = count(), revenue = sum(amount), avg_s = avg(score) by region",
            "SecurityEvents | summarize count() by bin(TimeGenerated, 1h)",
            "let Errors = AppLogs | where Level == 'Error';\nErrors | summarize count() by Service",
            "T | where Level == 'Error' | summarize total = count() by region | order by total desc | take 10",
            "SecurityEvents | union HoneypotHits | project source_ip",
            "SecurityEvents | join kind=inner (DeviceNetworkEvents) on DeviceId",
        ]
        for kql in REGISTRY:
            ir = to_semantic_ir(parse(kql))
            result = validate_ir(ir)
            if not result.is_valid:
                return False
        return True
    except Exception:
        return False


# ─── Report builder ───────────────────────────────────────────────────────────

def build_report(run_tier3: bool = True) -> dict:
    """Build the full convergence report dict."""
    print("\nConvergence Report Generator")
    print("=" * 45)

    # Tier 1
    print("  Running Tier 1 (25 cases)...", end=" ", flush=True)
    t1 = _run_tier(_get_tier1_cases(), "Tier 1")
    print(f"{t1['passing']}/{t1['total']}")

    # Tier 2
    print("  Running Tier 2 (10 cases)...", end=" ", flush=True)
    t2 = _run_tier(_get_tier2_cases(), "Tier 2")
    print(f"{t2['passing']}/{t2['total']}")

    # Tier 3
    t3: dict = {"total": 0, "passing": 0, "failing": 0, "rate": 0.0,
                "categories": {}, "failing_ids": []}
    if run_tier3:
        if TIER3_FILE.exists():
            raw = json.loads(TIER3_FILE.read_text())
            tier3_cases = [(q["id"], q["kql"]) for q in raw]
            print(f"  Running Tier 3 ({len(tier3_cases)} cases)...", end=" ", flush=True)
            t3 = _run_tier(tier3_cases, "Tier 3")
            print(f"{t3['passing']}/{t3['total']}")
        else:
            print("  Tier 3: tier3_queries.json not found — run extract_tier3.py")

    # Snapshot gate
    print("  Checking snapshot validator gate...", end=" ", flush=True)
    snap_ok = _check_snapshot_gate()
    print("PASS" if snap_ok else "FAIL")

    # Gate status
    gate = {
        "validator_snapshots": snap_ok,
        "tier1": t1["passing"] == t1["total"] and t1["total"] > 0,
        "tier2": t2["passing"] == t2["total"] and t2["total"] > 0,
        "tier3": t3["passing"] == t3["total"] and t3["total"] > 0,
    }
    gate["phase3b_complete"] = all(gate.values())

    # Merge category counts across tiers
    all_categories: dict[str, int] = {}
    for tier in (t1, t2, t3):
        for cat, count in tier.get("categories", {}).items():
            all_categories[cat] = all_categories.get(cat, 0) + count

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gate_status": gate,
        "tier1": {k: v for k, v in t1.items() if k != "failing_ids"},
        "tier2": {k: v for k, v in t2.items() if k != "failing_ids"},
        "tier3": {k: v for k, v in t3.items() if k != "failing_ids"},
        "all_categories": dict(sorted(all_categories.items(), key=lambda x: -x[1])),
        "failing_ids": {
            "tier1": t1.get("failing_ids", []),
            "tier2": t2.get("failing_ids", []),
            "tier3": t3.get("failing_ids", [])[:50],  # cap at 50 for readability
        },
    }
    return report


def print_summary(report: dict) -> None:
    gate = report["gate_status"]
    t1, t2, t3 = report["tier1"], report["tier2"], report["tier3"]

    print(f"\n{'='*50}")
    print("  CONVERGENCE SCOREBOARD")
    print(f"{'='*50}")
    print(f"  Tier 1:  {t1['passing']:>4}/{t1['total']:<4}  ({t1['rate']:>5.1f}%)")
    print(f"  Tier 2:  {t2['passing']:>4}/{t2['total']:<4}  ({t2['rate']:>5.1f}%)")
    if t3['total'] > 0:
        print(f"  Tier 3:  {t3['passing']:>4}/{t3['total']:<4}  ({t3['rate']:>5.1f}%)")
    else:
        print("  Tier 3:  not yet extracted")
    print(f"{'-'*50}")
    print(f"  Snapshots: {'PASS' if gate['validator_snapshots'] else 'FAIL'}")
    print(f"  Phase 3B Complete: {'[OK] YES' if gate['phase3b_complete'] else '[FAIL] NO'}")

    cats = report.get("all_categories", {})
    if cats:
        print("\n  Failure Categories:")
        for cat, count in list(cats.items())[:10]:
            bar = "#" * min(count, 30)
            print(f"  [{count:>4}] {bar}  {cat}")

    print(f"{'='*50}\n")


def append_history(report: dict) -> None:
    """
    Append a compact entry to convergence_history.json.

    History format (append-only — never overwritten):
        [
          {"timestamp": "...", "tier1": 25, "tier2": 10, "tier3": 281,
           "tier3_total": 353, "rate": 79.6, "gate": false},
          ...
        ]

    Used for:
      - GitHub Actions trend charts
      - Release readiness dashboards
      - Regression detection between sessions
      - Visualizing: 280/353 → 310/353 → 353/353
    """
    entry = {
        "timestamp": report["timestamp"],
        "tier1":       report["tier1"]["passing"],
        "tier1_total": report["tier1"]["total"],
        "tier2":       report["tier2"]["passing"],
        "tier2_total": report["tier2"]["total"],
        "tier3":       report["tier3"]["passing"],
        "tier3_total": report["tier3"]["total"],
        "rate":        report["tier3"]["rate"],
        "gate":        report["gate_status"]["phase3b_complete"],
    }

    history: list = []
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            history = []

    history.append(entry)

    HISTORY_FILE.write_text(
        json.dumps(history, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(REPORT_FILE))
    parser.add_argument("--no-tier3", action="store_true",
                        help="Skip Tier 3 (faster, for CI pre-checks)")
    args = parser.parse_args()

    report = build_report(run_tier3=not args.no_tier3)
    print_summary(report)

    out = Path(args.out)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    # Append compact entry to history (append-only — never overwritten)
    append_history(report)

    print(f"  Report written:  {out}")
    print(f"  History updated: {HISTORY_FILE}")
    print(f"  Gate: {'PASS — ready to flip translate()' if report['gate_status']['phase3b_complete'] else 'NOT YET — see failing categories'}\n")


if __name__ == "__main__":
    main()
