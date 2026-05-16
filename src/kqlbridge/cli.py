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
        print("[kqlbridge] Query contains unsupported operators.", file=sys.stderr)
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
    if not is_supported(kql):
        ops = detect_operators(kql)
        print("Unsupported")
        print(f"  Operators detected : {', '.join(ops) if ops else 'none'}")
        print("  Reason             : query uses unsupported operators or invalid syntax")
        return 1
    from kqlbridge import check
    result = check(kql)
    ops = detect_operators(kql)
    print("Supported")
    print(f"  Operators detected: {', '.join(ops) if ops else 'none'}")
    if result.warnings:
        for w in result.warnings:
            print(f"  WARNING: {w}")
    return 0


def _operators(args: argparse.Namespace) -> int:
    supported = [
        "where", "project", "summarize", "order by", "sort by",
        "take", "limit", "distinct", "extend", "join",
        "union", "count", "let", "ago()", "bin()",
        "and / or / not", "in", "has", "contains",
        "startswith", "endswith", "isnotnull", "isnull",
    ]
    print("KQLBridge v0.1 - supported operators:")
    for op in supported:
        print(f"  {op}")
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
        description="KQL to Spark SQL / T-SQL transpiler for Microsoft Fabric and Databricks",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    p_translate = sub.add_parser("translate", help="Translate KQL to SQL")
    p_translate.add_argument("kql", help="KQL query string")
    p_translate.add_argument("--tsql", action="store_true", help="Output T-SQL instead of Spark SQL")
    p_translate.set_defaults(func=_translate)

    p_check = sub.add_parser("check", help="Check if a KQL query is supported")
    p_check.add_argument("kql", help="KQL query string")
    p_check.set_defaults(func=_check)

    p_ops = sub.add_parser("operators", help="List all supported KQL operators")
    p_ops.set_defaults(func=_operators)

    p_ver = sub.add_parser("version", help="Show version")
    p_ver.set_defaults(func=_version)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(0)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
