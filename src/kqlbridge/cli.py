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
    if getattr(args, "tsql", False):
        target = "tsql"
    elif getattr(args, "pyspark", False):
        target = "pyspark"
    else:
        target = "spark"

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
    if getattr(args, "tsql", False):
        target = "tsql"
    elif getattr(args, "pyspark", False):
        target = "pyspark"
    else:
        target = "spark"
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


def _mlm(args: argparse.Namespace) -> int:
    from kqlbridge import mlm_agent
    
    subcmd = args.mlm_command
    if subcmd == "status":
        tel = mlm_agent.memory.get("telemetry", {})
        print("KQLBridge MLM Agent Status:")
        print(f"  Memory path        : {mlm_agent.memory_path}")
        print(f"  Total translations : {tel.get('total_translations', 0)}")
        print(f"  Success count      : {tel.get('success_count', 0)}")
        print(f"  Failures recorded  : {len(tel.get('failures', {}))}")
        print(f"  Active overrides   : {len(mlm_agent.memory.get('overrides', {}))}")
        print(f"  Active BML rules   : {len(mlm_agent.memory.get('rules', []))}")
        
        failures = tel.get('failures', {})
        if failures:
            print("\nRecorded Failures:")
            for query, info in failures.items():
                print(f"  - Query: {query}")
                print(f"    Count: {info.get('count', 0)}")
                print(f"    Error: {info.get('error', '')}")
                
        overrides = mlm_agent.memory.get("overrides", {})
        if overrides:
            print("\nActive Overrides:")
            for kql, sql in overrides.items():
                print(f"  - KQL: {kql}")
                print(f"    SQL: {sql}")

        rules = mlm_agent.memory.get("rules", [])
        if rules:
            print("\nActive Bridge Meta-Language Rules:")
            for rule in rules:
                print(f"  - Pattern: {rule['pattern']}")
                print(f"    Mapping: {rule['mapping']}")
                
        return 0

    elif subcmd == "override":
        kql = args.kql
        sql = args.sql
        mlm_agent.learn(kql, fix_sql=sql)
        print(f"✓ Registered static override for query:\n  KQL: {kql}\n  SQL: {sql}")
        return 0

    elif subcmd == "rule":
        pattern = args.pattern
        mapping = args.mapping
        mlm_agent.register_rule(pattern, mapping)
        print(f"✓ Registered dynamic BML rule:\n  Pattern: {pattern}\n  Mapping: {mapping}")
        return 0

    elif subcmd == "clear":
        mlm_agent.clear()
        print("✓ MLM memory and telemetries successfully cleared.")
        return 0

    elif subcmd == "suggest":
        kql = args.kql
        failures = mlm_agent.memory.get("telemetry", {}).get("failures", {})
        norm_kql = " ".join(kql.strip().split())
        error_msg = failures.get(norm_kql, {}).get("error", "Unknown transpilation gap")
        
        print(f"Analyzing transpilation gap for query: {kql}")
        print(f"Error context: {error_msg}")
        print("Querying AI suggestion engine...")
        
        suggested_sql = mlm_agent.suggest_fix_via_ai(kql, error_msg)
        if suggested_sql:
            print("\nAI Suggested SQL Transpilation:")
            print(f"  {suggested_sql}")
            print("\nWould you like to register this override? Run:")
            print(f"  kqlbridge mlm override {args.kql!r} {suggested_sql!r}")
        else:
            print("\n✗ AI Suggestion engine failed to resolve this query.")
        return 0

    return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kqlbridge",
        description="KQL → Spark SQL / T-SQL transpiler for Microsoft Fabric and Databricks",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # translate
    p_translate = sub.add_parser("translate", help="Translate KQL to SQL/Python")
    p_translate.add_argument("kql", help="KQL query string")
    p_translate.add_argument("--tsql", action="store_true", help="Output T-SQL instead of Spark SQL")
    p_translate.add_argument("--pyspark", action="store_true", help="Output PySpark DataFrame Python code")
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
    p_explain.add_argument("--pyspark", action="store_true",
        help="Explain PySpark DataFrame Python code")
    p_explain.set_defaults(func=_explain)

    p_lint = sub.add_parser("lint", help="Detect semantic drift in AI-generated KQL")
    p_lint.add_argument("kql", help="KQL query string")
    p_lint.set_defaults(func=_lint)

    p_ops = sub.add_parser("operators", help="List all supported KQL operators")
    p_ops.set_defaults(func=_operators)

    # version
    p_ver = sub.add_parser("version", help="Show version")
    p_ver.set_defaults(func=_version)

    # mlm
    p_mlm = sub.add_parser("mlm", help="Manage the Micro Language Model (MLM) Agent")
    mlm_sub = p_mlm.add_subparsers(dest="mlm_command", metavar="<mlm-command>")

    # mlm status
    p_mlm_status = mlm_sub.add_parser("status", help="Print MLM memory diagnostics and recorded failures")
    p_mlm_status.set_defaults(func=_mlm)

    # mlm override
    p_mlm_override = mlm_sub.add_parser("override", help="Manually register an exact query translation override")
    p_mlm_override.add_argument("kql", help="Target KQL query string")
    p_mlm_override.add_argument("sql", help="Target SQL query string")
    p_mlm_override.set_defaults(func=_mlm)

    # mlm rule
    p_mlm_rule = mlm_sub.add_parser("rule", help="Register a dynamic Bridge Meta-Language (BML) pattern rule")
    p_mlm_rule.add_argument("pattern", help="Bridge Meta-Language pattern template (e.g. 'T | custom({col})')")
    p_mlm_rule.add_argument("mapping", help="Bridge Meta-Language SQL mapping template (e.g. 'SELECT {col} FROM T')")
    p_mlm_rule.set_defaults(func=_mlm)

    # mlm clear
    p_mlm_clear = mlm_sub.add_parser("clear", help="Clear all recorded failures, overrides, and telemetries")
    p_mlm_clear.set_defaults(func=_mlm)

    # mlm suggest
    p_mlm_suggest = mlm_sub.add_parser("suggest", help="Leverage AI analysis to suggest an override for a failed query")
    p_mlm_suggest.add_argument("kql", help="Target KQL query string that failed translation")
    p_mlm_suggest.set_defaults(func=_mlm)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    # Make sure subcommands also have default func if needed, or if main command handles routing
    if not hasattr(args, "func"):
        p_mlm.print_help()
        sys.exit(0)

    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
