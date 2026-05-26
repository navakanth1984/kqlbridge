import sys
import os
sys.path.insert(0, os.path.abspath('src'))
from kqlbridge.parser import parse
from kqlbridge import lint, smart_transpile
import traceback
import os
tests = {
    "Layer 2: Type Coercion & SQL Injection Literals": """
SecurityEvents
| extend int_max = 2147483647
| extend bigint_max = 9223372036854775807
| extend float_max = 1.7976931348623158
| extend sqli_classic = "' OR '1'='1"
| extend sqli_drop = '"; DROP TABLE users;--'
| extend tpli_probe = "${7*7}"
| project int_max, bigint_max, float_max, sqli_classic, sqli_drop, tpli_probe
""",
    "Layer 3: Aggregation (Basic Group By allowed)": """
SecurityEvents
| summarize events_per_src = count() by source_ip
""",
    "Layer 4: Threat Scoring (Nested IFF logic)": """
SecurityEvents
| extend threat_level = iff(events_per_src > 10000, "CRITICAL", iff(events_per_src <= 10, "MEDIUM", "LOW"))
| project threat_level
""",
    "Layer 5: Correlated Subqueries / Subquery IN": """
SecurityEvents
| where source_ip in ("1.2.3.4", "5.6.7.8")
""",
    "Layer 6: Set Operations (UNION)": """
SecurityEvents
| union HoneypotHits
| project source_ip
""",
    "Security: Deep nesting": """
SecurityEvents
| where (((((((((((event_id == 4624)))))))))))
""",
    "Semantic Drift: =~ Operator": """
SecurityEvents
| where username =~ "Admin"
""",
    "Semantic Drift: Has Operator": """
SecurityEvents
| where message has "error"
""",
    "Complex Join and Aggregation": """
let RecentErrors = SecurityEvents | where Level == 'Error' | where TimeGenerated > ago(1d);
RecentErrors
| join kind=inner (DeviceNetworkEvents | where ActionType == 'ConnectionFailed') on DeviceId
| summarize failures = count() by bin(TimeGenerated, 1h), DeviceId
""",
    "Complex Let Bindings": """
let T1 = Table1 | extend factor = 100;
let T2 = Table2 | extend factor = 200;
T1 | union T2 | project factor, id
""",
    "Complex Filtering and Extend": """
SecurityEvents
| where TimeGenerated > ago(7d) and (Level == 'Error' or (Level == 'Warning' and Message has 'timeout'))
| extend is_critical = iff(Level == 'Error', true, false)
| project TimeGenerated, is_critical
""",
    "Complex Summarize and Order": """
SecurityEvents
| summarize total = count(), critical = countif(Level == 'Error'), distinct_ips = dcount(source_ip) by bin(TimeGenerated, 1d)
| order by total desc
| take 10
""",
    "Complex Endswith & Startswith Pattern Match": """
SecurityEvents
| where Message startswith "login" or Message endswith "failed"
| project Message
""",
    "Arithmetic Operator Precedence Stress": """
Orders
| extend cost = (UnitPrice * Quantity) * (1.0 - Discount) + ShippingFee
| project OrderId, cost
""",
    "String Manipulation and Length functions": """
SecurityEvents
| extend normalized = tolower(trim(username)), len = strlen(username)
| project normalized, len
""",
    "Logical Operators AND, OR, NOT combinatorics": """
SecurityEvents
| where not(Level == 'Info' or Level == 'Debug') and (EventID == 4624 or EventID == 4625)
| project EventID, Level
""",
    "Let statements with nested expressions and variables": """
let CriticalIPs = SecurityEvents | where Severity >= 4 | project source_ip;
SecurityEvents
| where source_ip in (CriticalIPs)
| summarize count() by source_ip
""",
    "Chained extends referencing previous extends": """
SecurityEvents
| extend base_score = 50
| extend final_score = base_score + 10
| project final_score
""",
    "Unsupported Window Function": """
SecurityEvents
| serialize 
| extend prev_event = prev(event_id)
"""
}

raw_sql_injection = """
WITH
recursive_depth AS (
    SELECT
        1                        AS depth,
        CAST('root' AS VARCHAR)  AS path,
        CAST(0 AS BIGINT)        AS accumulated_cost
    UNION ALL
    SELECT
        rd.depth + 1,
        CAST(rd.path + '/' + CAST(rd.depth AS VARCHAR) AS VARCHAR),
        rd.accumulated_cost + (rd.depth * rd.depth)
    FROM recursive_depth rd
    WHERE rd.depth < 64
)
SELECT * FROM recursive_depth
"""

def run():
    print("========================================")
    print("KQLBridge Stress & Security Probes v0.6.0")
    print("========================================\n")
    
    print("--- RAW SQL ADVERSARIAL PAYLOAD ---")
    try:
        parse(raw_sql_injection.strip())
        print("FAILED: Parser unexpectedly allowed raw SQL.")
    except Exception as e:
        print(f"SUCCESS (Rejected correctly): {type(e).__name__} blocked the raw SQL injection attempt.\n")

    for name, kql in tests.items():
        print(f"--- {name} ---")
        if not kql.strip():
            print("Skipped (No KQL equivalent tested)\n")
            continue
            
        lint_result = lint(kql.strip())
        if lint_result.issues:
            print("Lint Warnings:")
            for issue in lint_result.issues:
                print(f"  [{issue.rule_id}] {issue.severity.upper()}:")
                print(f"    Intent:    {issue.kql_intent}")
                print(f"    Behaviour: {issue.sql_behaviour}")
                print(f"    Fix:       {issue.fix}")
        
        try:
            engine, code = smart_transpile(kql.strip())
            print(f"Smart Transpile (Routed to: {engine}):")
            print(code.strip())
            print("")
            _, pyspark_code = smart_transpile(kql.strip(), force_engine="pyspark")
            print("PySpark Generator (Forced):")
            print(pyspark_code.strip())
            print("")
        except Exception as e:
            print(f"FAILED: {type(e).__name__}: {e}")
            os.makedirs(".jules", exist_ok=True)
            log_name = name.replace(" ", "_").replace(":", "").replace("/", "")
            with open(f".jules/stress_{log_name}.md", "w") as f:
                f.write(f"# FAILURE: {name}\n\n**KQL:**\n```kusto\n{kql.strip()}\n```\n\n**Traceback:**\n```python\n{traceback.format_exc()}\n```\n")

if __name__ == '__main__':
    run()
