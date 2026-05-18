"""
cli.py — KQLBridge command-line interface
==========================================
Entry point declared in pyproject.toml:
    kqlbridge = "kqlbridge.cli:main"

Commands:
    kqlbridge translate "<KQL>"          Translate KQL → Spark SQL (default)
    kqlbridge translate "<KQL>" --tsql   Translate KQL → T-SQL
    kqlbridge check "<KQL>"              Check if KQL is supported (exit 0/1)
    kqlbridge operators                  List all supported operators
    kqlbridge version                    Show version
"""

from __future__ import annotations
import argparse
import sys


def _translate(args: argparse.Namespace) -> int:
    from kqlbridge import translate, is_supported

    kql = args.kql
    target = "tsql" if getattr(args, "tsql", False) else "spark"

    if not is_supported(kql):
        print("[kqlbridge] ✗ Query contains unsupported operators.", file=sys.stderr)
        print("[kqlbridge] Run 'kqlbridge check' for details.", file=sys.stderr)
        return 1

    try:
        sql = translate(kql, target=target)
        print(sql)
        return 0
    except Exception as e:
        print(f"[kqlbridge] Translation error: {e}", file=sys.stderr)
        return 1


def _check(args: argparse.Namespace) -> int:
    from kqlbridge import is_supported, detect_operators

    kql = args.kql

    # Use is_supported() first — it catches parse errors gracefully
    if not is_supported(kql):
        ops = detect_operators(kql)
        print("✗ Unsupported")
        print(f"  Operators detected : {', '.join(ops) if ops else 'none'}")
        print("  Reason             : query uses unsupported operators or invalid syntax")
        return 1

    from kqlbridge import check
    result = check(kql)
    ops = detect_operators(kql)

    print("✓ Supported")
    print(f"  Operators detected: {', '.join(ops) if ops else 'none'}")
    if result.warnings:
        for w in result.warnings:
            print(f"  ⚠  {w}")
    return 0



def _lint(args) -> int:
    from kqlbridge.lint import lint
    kql = args.kql
    result = lint(kql)

    if result.is_clean:
        print("✓ CLEAN — no semantic drift detected")
        return 0

    print(f"⚠  SEMANTIC DRIFT DETECTED — {len(result.issues)} issue(s)  [risk: {result.risk}]")
    print()
    for i, issue in enumerate(result.issues, 1):
        print(f"[{issue.rule_id}] {issue.severity} — {issue.operator}")
        print(f"  KQL intent : {issue.kql_intent}")
        print(f"  SQL does   : {issue.sql_behaviour}")
        print(f"  Fix        : {issue.fix}")
        print()

    return 1



def _explain(args) -> int:
    from kqlbridge.explain import explain
    import sys
    target = "tsql" if getattr(args, "tsql", False) else "spark"
    try:
        result = explain(args.kql, target=target)
        print(result.annotated_sql)
        print()
        print(result.summary)
        return 0
    except ValueError as e:
        print(f"[kqlbridge] {e}", file=sys.stderr)
        return 1


def _operators(args: argparse.Namespace) -> int:
    supported = [
        "where", "project", "summarize", "order by", "sort by",
        "take", "limit", "distinct", "extend", "join",
        "union", "count", "let", "ago()", "bin()",
        "and / or / not", "in", "has", "contains",
        "startswith", "endswith", "isnotnull", "isnull",
    ]
    print("KQLBridge v0.1 — supported operators:")
    for op in supported:
        print(f"  ✓  {op}")
    return 0


def _version(args: argparse.Namespace) -> int:
    from importlib.metadata import version, PackageNotFoundError
    try:
        v = version("kqlbridge")
    except PackageNotFoundError:
        v = "dev"
    print(f"kqlbridge {v}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kqlbridge",
        description="KQL → Spark SQL / T-SQL transpiler for Microsoft Fabric and Databricks",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # translate
    p_translate = sub.add_parser("translate", help="Translate KQL to SQL")
    p_translate.add_argument("kql", help="KQL query string")
    p_translate.add_argument("--tsql", action="store_true", help="Output T-SQL instead of Spark SQL")
    p_translate.set_defaults(func=_translate)

    # check
    p_check = sub.add_parser("check", help="Check if a KQL query is supported")
    p_check.add_argument("kql", help="KQL query string")
    p_check.set_defaults(func=_check)

    # operators
    p_explain = sub.add_parser("explain",
        help="Translate KQL with inline annotations explaining every decision")
    p_explain.add_argument("kql", help="KQL query string")
    p_explain.add_argument("--tsql", action="store_true",
        help="Explain T-SQL output instead of Spark SQL")
    p_explain.set_defaults(func=_explain)

    p_lint = sub.add_parser("lint", help="Detect semantic drift in AI-generated KQL")
    p_lint.add_argument("kql", help="KQL query string")
    p_lint.set_defaults(func=_lint)

    p_ops = sub.add_parser("operators", help="List all supported KQL operators")
    p_ops.set_defaults(func=_operators)

    # version
    p_ver = sub.add_parser("version", help="Show version")
    p_ver.set_defaults(func=_version)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
