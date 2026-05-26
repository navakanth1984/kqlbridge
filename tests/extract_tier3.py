"""
tests/extract_tier3.py — Phase 3B Benchmark Extractor
=======================================================
Extracts the 353-query baseline from your eval benchmark file and writes
it to tests/tier3_queries.json for use by test_tier3_convergence.py.

Handles multiple benchmark formats automatically:
  - List of strings:           ["T | where x == 1", ...]
  - List of dicts with "kql":  [{"kql": "T | ...", "id": "q001"}, ...]
  - List of dicts with "query": [{"query": "T | ...", ...}, ...]
  - Nested dict with "queries": {"queries": ["T | where...", ...]}
  - KQLBridge eval format:     {"cases": [{"input": "T | where...", ...}]}

Run:
    py tests/extract_tier3.py
    py tests/extract_tier3.py --source tests/eval/benchmark.json
    py tests/extract_tier3.py --source tests/eval/benchmark.json --out tests/tier3_queries.json

Output: tests/tier3_queries.json
    [
      {"id": "q001", "kql": "T | where x == 1"},
      ...
    ]

After extraction:
    py -m pytest tests/test_tier3_convergence.py -v
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DEFAULT_SOURCES = [
    "tests/eval/benchmark.json",
    "tests/eval/queries.json",
    "tests/eval/kql_queries.json",
    "tests/data/benchmark.json",
    "tests/eval/eval.json",
    "benchmark.json",
    "eval.json",
]
DEFAULT_OUT = "tests/tier3_queries.json"


def find_source(explicit: str | None) -> Path | None:
    """Find the benchmark file — explicit path or auto-detect."""
    if explicit:
        p = Path(explicit)
        if not p.is_absolute():
            p = ROOT / explicit
        if p.exists():
            return p
        sys.exit(f"ERROR: Specified source not found: {p}")

    for candidate in DEFAULT_SOURCES:
        p = ROOT / candidate
        if p.exists():
            print(f"  Auto-detected: {candidate}")
            return p

    return None


def extract_queries(data: object) -> list[dict]:
    """
    Normalise any benchmark format into a list of {"id": ..., "kql": ...} dicts.
    Handles all common shapes.
    """
    queries: list[dict] = []

    # ── Shape 1: plain list ─────────────────────────────────────────────
    if isinstance(data, list):
        for i, item in enumerate(data):
            qid = f"q{i+1:04d}"
            if isinstance(item, str):
                queries.append({"id": qid, "kql": item.strip()})
            elif isinstance(item, dict):
                kql = (
                    item.get("kql") or
                    item.get("query") or
                    item.get("input") or
                    item.get("kql_query") or
                    item.get("text") or
                    ""
                ).strip()
                qid = str(item.get("id") or item.get("name") or qid)
                if kql:
                    queries.append({"id": qid, "kql": kql})
        return queries

    # ── Shape 2: top-level dict with a list inside ──────────────────────
    if isinstance(data, dict):
        for key in ("queries", "cases", "tests", "items", "data", "kql_queries"):
            if key in data and isinstance(data[key], list):
                return extract_queries(data[key])

    return queries


def validate_kql_list(queries: list[dict]) -> list[dict]:
    """Remove empty entries and deduplicate."""
    seen: set[str] = set()
    clean: list[dict] = []
    skipped_empty = 0
    skipped_dup = 0

    for q in queries:
        kql = q.get("kql", "").strip()
        if not kql:
            skipped_empty += 1
            continue
        if kql in seen:
            skipped_dup += 1
            continue
        seen.add(kql)
        clean.append({"id": q["id"], "kql": kql})

    if skipped_empty:
        print(f"  Skipped {skipped_empty} empty entries")
    if skipped_dup:
        print(f"  Skipped {skipped_dup} duplicate queries")

    return clean


def main():
    parser = argparse.ArgumentParser(description="Extract Tier 3 benchmark queries")
    parser.add_argument("--source", help="Path to benchmark JSON (auto-detected if omitted)")
    parser.add_argument("--out", default=DEFAULT_OUT, help="Output path")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max queries to extract (0 = all)")
    args = parser.parse_args()

    print("\nPhase 3B — Tier 3 Query Extractor")
    print("=" * 40)

    # Find source
    source = find_source(args.source)
    if source is None:
        print("\nERROR: No benchmark file found.")
        print("Searched:")
        for s in DEFAULT_SOURCES:
            print(f"  {s}")
        print("\nRun with --source <path> to specify the file.")
        print("Or check where KQLBridge stores its eval queries:")
        print("  find . -name '*.json' | xargs grep -l '\"kql\"\\|\"query\"' | head -10")
        sys.exit(1)

    print(f"  Source: {source.relative_to(ROOT)}")

    # Load and extract
    raw = json.loads(source.read_text(encoding="utf-8"))
    queries = extract_queries(raw)

    if not queries:
        print("\nERROR: No queries extracted.")
        print("File content preview (first 500 chars):")
        print(source.read_text()[:500])
        print("\nEdit SNAPSHOT_REGISTRY in extract_tier3.py to match your format.")
        sys.exit(1)

    queries = validate_kql_list(queries)

    if args.limit > 0:
        queries = queries[:args.limit]
        print(f"  Limited to {args.limit} queries")

    # Write output
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(queries, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"  Extracted: {len(queries)} queries")
    print(f"  Output: {args.out}")
    print("\nNext step:")
    print("  py -m pytest tests/test_tier3_convergence.py -v")
    print("  py -m pytest tests/test_tier3_convergence.py -v --tb=short -q")
    print()


if __name__ == "__main__":
    main()
