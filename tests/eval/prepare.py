"""
prepare.py — KQLBridge Eval Oracle
===================================
LOCKED FILE — Agent MUST NEVER modify this file or benchmark.json.

This is the single source of truth for KQLBridge's translation quality.
The agent's only interaction with this file is reading its output score.

If the agent can rewrite the rules of success, it will — and scores
become meaningless. This file is protected by CODEOWNERS.

Scoring:
    Each case is scored PASS (1) or FAIL (0).
    PASS requires BOTH:
    a) Syntactic validity: sqlglot can parse the output as Spark SQL
    b) Structural equivalence: canonical form matches expected_sql canonical form

    Score = (passed / total) * 100
    Target: >= 85.0%

Time budget: 30 seconds per case (enforced with signal).
"""

import json
import signal
import sys
import re
from pathlib import Path
from typing import Optional

# ─── WINDOWS UTF-8 COMPATIBILITY ─────────────────────────────────────────────
# Fix UnicodeEncodeError on Windows terminals that default to cp1252
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Progress bar chars — fall back to ASCII if terminal can't handle UTF-8
try:
    "█░".encode(sys.stdout.encoding or "utf-8")
    _BAR_FULL, _BAR_EMPTY = "█", "░"
except (UnicodeEncodeError, LookupError):
    _BAR_FULL, _BAR_EMPTY = "#", "-"

# ─── SETUP ───────────────────────────────────────────────────────────────────

BENCHMARK_PATH = Path(__file__).parent / "benchmark.json"
TIME_BUDGET = 30  # seconds per case — matches program.md contract


def _timeout_handler(signum, frame):
    raise TimeoutError("Case exceeded 30-second time budget")


try:
    import sqlglot
    HAS_SQLGLOT = True
except ImportError:
    HAS_SQLGLOT = False
    print("[WARN] sqlglot not installed — syntactic check disabled", file=sys.stderr)


try:
    from kqlbridge import translate
    HAS_KQLBRIDGE = True
except ImportError:
    HAS_KQLBRIDGE = False
    print("[ERROR] kqlbridge not importable — install with: pip install -e .", file=sys.stderr)
    sys.exit(1)


# ─── CANONICAL FORM ──────────────────────────────────────────────────────────

def _canonicalize(sql: str) -> str:
    """
    Normalize a SQL string for structural comparison.

    Operations:
    - Lowercase all keywords
    - Collapse all whitespace (including newlines) to single space
    - Strip leading/trailing whitespace
    - Normalize string quotes to single quotes
    - Remove trailing semicolons

    This is intentionally simple and conservative. The goal is to catch
    structural mismatches, not byte-for-byte equality.
    """
    s = sql.strip().rstrip(";")
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s)
    # Lowercase
    s = s.lower()
    # Normalize double-quoted strings → single-quoted
    s = re.sub(r'"([^"]*)"', lambda m: f"'{m.group(1)}'", s)
    return s


def _canonical_match(actual: str, expected: str) -> bool:
    """Check structural equivalence via canonical form."""
    return _canonicalize(actual) == _canonicalize(expected)


# ─── SYNTAX CHECK ─────────────────────────────────────────────────────────────

def _is_syntactically_valid(sql: str) -> bool:
    """Check that the generated SQL is parseable by sqlglot as Spark SQL."""
    if not HAS_SQLGLOT:
        return True  # Skip if sqlglot not available
    try:
        parsed = sqlglot.parse(sql, dialect="spark")
        return len(parsed) > 0 and parsed[0] is not None
    except Exception:
        return False


# ─── SCORE ONE CASE ──────────────────────────────────────────────────────────

def score_one(case: dict) -> tuple[int, Optional[str]]:
    """
    Score a single benchmark case.

    Returns (score: int, failure_reason: Optional[str])
    score = 1 (PASS) or 0 (FAIL)
    """
    # Set time budget
    if hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(TIME_BUDGET)

    try:
        result = translate(case["kql"], target="spark")

        # Check 1: syntactic validity
        if not _is_syntactically_valid(result):
            return 0, f"Syntactically invalid SQL: {result[:120]!r}"

        # Check 2: structural equivalence
        if not _canonical_match(result, case["expected_sql"]):
            return 0, (
                f"Mismatch:\n"
                f"  GOT:      {_canonicalize(result)[:160]}\n"
                f"  EXPECTED: {_canonicalize(case['expected_sql'])[:160]}"
            )

        return 1, None

    except TimeoutError:
        return 0, f"Timed out after {TIME_BUDGET}s"

    except NotImplementedError as e:
        return 0, f"Not implemented: {e}"

    except Exception as e:
        return 0, f"Exception: {type(e).__name__}: {e}"

    finally:
        if hasattr(signal, "SIGALRM"):
            signal.alarm(0)


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main() -> float:
    benchmark = json.loads(BENCHMARK_PATH.read_text())

    results = []
    failures = []

    for case in benchmark:
        score, reason = score_one(case)
        results.append(score)
        if reason:
            failures.append((case["id"], case["description"], reason))

    total = len(results)
    passed = sum(results)
    pct = (passed / total) * 100 if total > 0 else 0.0

    # ─── Output ───────────────────────────────────────────────────────────
    print(f"\nKQLBridge Eval — {Path(__file__).stem}")
    print("=" * 60)

    # Category breakdown
    by_category: dict[str, list[int]] = {}
    for i, case in enumerate(benchmark):
        cat = case.get("category", "unknown")
        by_category.setdefault(cat, []).append(results[i])

    for cat, scores in sorted(by_category.items()):
        cat_passed = sum(scores)
        cat_total = len(scores)
        bar = _BAR_FULL * cat_passed + _BAR_EMPTY * (cat_total - cat_passed)
        print(f"  {cat:12s} {bar} {cat_passed}/{cat_total}")

    print("=" * 60)
    print(f"SCORE: {pct:.1f}% ({passed}/{total})")

    if failures:
        print(f"\nFailed ({len(failures)} cases):")
        for case_id, desc, reason in failures:
            print(f"\n  [{case_id}] {desc}")
            for line in reason.splitlines():
                print(f"    {line}")

    # Exit code for CI: 0 = score >= 85%, 1 = below target
    target = 85.0
    if pct >= target:
        print(f"\n✅ Target met: {pct:.1f}% >= {target}%")
        return pct
    else:
        print(f"\n❌ Below target: {pct:.1f}% < {target}%")
        sys.exit(1)


if __name__ == "__main__":
    main()
