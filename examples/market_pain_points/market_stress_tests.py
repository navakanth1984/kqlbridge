import sys
import os
import traceback
from kqlbridge import translate, is_supported, detect_operators

# Market Stress Tests - Based on Real-World Pain Points and Community Research
# Target: Migration from ADX/Kusto to Spark/Fabric SQL

MARKET_TESTS = {
    "Legacy Migration: Multi-Join Trap": {
        "description": "Enterprise-scale join between 3 large tables with pre-filtering.",
        "problem": "SQL users often join then filter; KQL users filter then join. We test if filters are preserved.",
        "kql": """
let ErrorLogs = AppLogs | where Level == 'Error' | where TimeGenerated > ago(24h);
let DeviceInfo = Devices | where OS == 'Windows';
ErrorLogs
| join kind=inner (DeviceInfo) on DeviceId
| join kind=leftouter (UserDirectory | where Department == 'IT') on UserId
| project TimeGenerated, Message, DeviceName, Department
"""
    },
    "High-Cardinality Aggregations": {
        "description": "Summarizing by high-cardinality IDs with complex metrics.",
        "problem": "Aggregation on millions of unique SessionIds can crash memory. SQL needs efficient grouping.",
        "kql": """
AppLogs
| where TimeGenerated > ago(7d)
| summarize
    TotalEvents = count(),
    UniqueUsers = dcount(UserId),
    Errors = countif(Level == 'Error'),
    AvgLatency = avg(Duration)
  by SessionId, bin(TimeGenerated, 5m)
| where TotalEvents > 100
| order by TotalEvents desc
"""
    },
    "JSON Extraction at Scale": {
        "description": "Parsing nested JSON fields from telemetry streams.",
        "problem": "Query-time JSON parsing (parse_json) is a major bottleneck in Spark SQL if not optimized.",
        "kql": """
Telemetry
| extend data = parse_json_path(RawData, 'properties')
| extend region = tostring(parse_json_path(RawData, 'region'))
| extend severity = toint(parse_json_path(RawData, 'severity'))
| where region == 'eastus' and severity >= 3
| project TimeGenerated, region, severity, data
"""
    },
    "Deeply Nested Risk Scoring": {
        "description": "Security risk assessment using nested IFF logic.",
        "problem": "Deeply nested CASE statements in SQL can be hard to read and optimize.",
        "kql": """
SecurityEvents
| extend risk_score = iff(Severity >= 5, "CRITICAL",
    iff(Severity >= 3 and EventID in (4624, 4625), "HIGH",
        iff(Message has "admin" or Message has "root", "MEDIUM", "LOW")
    )
)
| summarize count() by risk_score, bin(TimeGenerated, 1h)
"""
    },
    "Union of Regional Sources": {
        "description": "Merging many disparate data sources into a global view.",
        "problem": "Unioning many tables (UNION ALL) can lead to large query plans in Spark.",
        "kql": """
union Logs_US, Logs_EU, Logs_ASIA, Logs_LATAM
| where TimeGenerated > ago(1h)
| where Level == 'Critical'
| summarize count() by Region = tostring(parse_json_path(RawData, 'region'))
"""
    },
    "Pattern Match Stress (Has/Contains)": {
        "description": "Complex text filtering using case-insensitive 'has' and 'contains'.",
        "problem": "KQL 'has' is whole-token aware and case-insensitive. SQL 'LIKE' or 'RLIKE' must match this semantic exactly.",
        "kql": """
AuditLogs
| where OperationName has "Delete" or OperationName contains "Security"
| where Message =~ "Access Denied" or Message startswith "Failed"
| project TimeGenerated, OperationName, Message
"""
    },
    "Time-Series Binning Combinatorics": {
        "description": "Complex time-binning with various intervals.",
        "problem": "Spark SQL's DATE_TRUNC doesn't support 5m/15m intervals easily. Testing custom binning logic.",
        "kql": """
Metrics
| summarize avg(Value) by bin(TimeGenerated, 15m), MetricName
| order by TimeGenerated asc
"""
    }
}

def run_market_stress_tests():
    print("====================================================")
    print("KQLBridge Market Stress Tests - v0.8.0")
    print("Analyzing Real-World Migration Pain Points")
    print("====================================================\n")

    for name, data in MARKET_TESTS.items():
        print(f"--- TEST CASE: {name} ---")
        print(f"Problem: {data['problem']}")
        kql = data['kql'].strip()

        # 1. Check Support
        supported = is_supported(kql)
        print(f"Supported: {'YES' if supported else 'NO'}")

        # 2. Detect Operators
        ops = detect_operators(kql)
        print(f"Operators: {', '.join(ops)}")

        # 3. Translate to Spark SQL
        try:
            print("\n>>> Translating to Spark SQL...")
            spark_sql = translate(kql, target="spark")
            print(spark_sql)
        except Exception as e:
            print(f"SPARK TRANSLATION FAILED: {type(e).__name__}: {e}")
            # traceback.print_exc()

        # 4. Translate to T-SQL
        try:
            print("\n>>> Translating to T-SQL...")
            tsql = translate(kql, target="tsql")
            print(tsql)
        except Exception as e:
            print(f"T-SQL TRANSLATION FAILED: {type(e).__name__}: {e}")

        print("-" * 50 + "\n")

if __name__ == "__main__":
    run_market_stress_tests()
