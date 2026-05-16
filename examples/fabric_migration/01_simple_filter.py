"""
examples/fabric_migration/01_simple_filter.py
=============================================
Real-world KQLBridge usage example — Microsoft Fabric migration pattern.

Scenario: A data engineering team has existing KQL queries running in
Eventhouse and wants to run the same logic in Fabric Spark notebooks
for large-scale batch processing.

This example shows the complete routing pattern used in the DE-Context Kit.
"""

from kqlbridge import translate, is_supported, detect_operators, check

# ─── Example 1: Simple filter + aggregation ─────────────────────────────────

kql_simple = """
AppLogs
| where TimeGenerated > ago(24h)
| where Level == 'Error'
| summarize count() by ServiceName
| order by count_ desc
| take 10
"""

if is_supported(kql_simple):
    spark_sql = translate(kql_simple.strip(), target="spark")
    print("=== Simple Filter + Aggregation ===")
    print(spark_sql)
    print()

# Expected output:
# SELECT ServiceName, COUNT(*)
# FROM AppLogs
# WHERE (TimeGenerated > CURRENT_TIMESTAMP - INTERVAL '24 hours' AND Level = 'Error')
# GROUP BY ServiceName
# ORDER BY count_ DESC
# LIMIT 10


# ─── Example 2: Time-series bucketing ───────────────────────────────────────

kql_timeseries = """
AppLogs
| where TimeGenerated > ago(7d)
| where Level == 'Error'
| summarize error_count = count() by bin(TimeGenerated, 1h), ServiceName
| order by TimeGenerated asc
"""

if is_supported(kql_timeseries):
    spark_sql = translate(kql_timeseries.strip(), target="spark")
    print("=== Time-Series Bucketing ===")
    print(spark_sql)
    print()


# ─── Example 3: Let variable → CTE ──────────────────────────────────────────

kql_let = """
let errors = AppLogs | where Level == 'Error' | where TimeGenerated > ago(24h);
let services = errors | summarize n = count() by ServiceName;
services | order by n desc | take 5
"""

if is_supported(kql_let):
    spark_sql = translate(kql_let.strip(), target="spark")
    print("=== Let Variables → CTEs ===")
    print(spark_sql)
    print()


# ─── Example 4: Routing agent pattern ───────────────────────────────────────

def route_query(kql: str) -> dict:
    """
    The routing agent pattern from DE-Context Kit.
    Routes each query to the most appropriate engine.
    """
    # Fast path: detect any unsupported operators
    if not is_supported(kql):
        result = check(kql)
        return {
            "engine": "kql",
            "sql": kql,
            "reason": "unsupported operators",
            "errors": result.errors,
            "warnings": result.warnings,
        }

    operators = detect_operators(kql)
    spark_sql = translate(kql, target="spark")

    return {
        "engine": "spark",
        "sql": spark_sql,
        "operators_used": operators,
    }


# Test routing
queries = [
    "AppLogs | where Level == 'Error' | summarize count() by ServiceName",
    "AppLogs | make-series count() on TimeGenerated step 1h",  # unsupported
    "AppLogs | where Level in ('Error', 'Warning') | order by TimeGenerated desc | take 100",
]

print("=== Routing Agent Demo ===")
for q in queries:
    result = route_query(q)
    print(f"Query: {q[:60]}...")
    print(f"Engine: {result['engine']}")
    if result['engine'] == 'spark':
        print(f"Operators: {result['operators_used']}")
        print(f"SQL: {result['sql'][:100]}...")
    else:
        print(f"Reason: {result['reason']}")
    print()
