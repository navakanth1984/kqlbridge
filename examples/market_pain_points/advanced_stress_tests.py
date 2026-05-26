from kqlbridge import translate, is_supported, detect_operators

# ADVANCED STRESS TESTS - Pushing the limits with Sentinel/ADX Patterns
# These cases focus on advanced aggregation, complex joins, and statistical patterns.

ADVANCED_TESTS = {
    "Advanced: Beaconing Jitter Analysis": {
        "description": "Calculating jitter between network connections to detect C2 traffic.",
        "kql": """
let Lookback = 1d;
CommonSecurityLog
| where TimeGenerated > ago(Lookback)
| where DeviceAction == "allow"
| extend TimeDiff = datetime_diff('second', TimeGenerated, prev(TimeGenerated))
| summarize 
    TotalEvents = count(), 
    AvgDelta = avg(TimeDiff), 
    StdDelta = stdev(TimeDiff) 
    by SourceIP, DestinationIP, DestinationPort
| where TotalEvents > 50 and StdDelta < 10
| order by StdDelta asc
"""
    },
    "Advanced: Lateral Movement Hunting": {
        "description": "Sequential login pattern matching using multiple joins and distinct counts.",
        "kql": """
let Logins = SecurityEvent 
    | where EventID == 4624 
    | project LoginTime=TimeGenerated, Computer, Account;
let AdministrativeActions = SecurityEvent
    | where EventID == 4672
    | project AdminTime=TimeGenerated, Computer, Account;
Logins
| join kind=inner (AdministrativeActions) on Computer, Account
| where datetime_diff('minute', AdminTime, LoginTime) between (0 .. 5)
| summarize PrivilegeEscalationCount = count() by Account, Computer, bin(LoginTime, 1h)
| where PrivilegeEscalationCount > 1
"""
    },
    "Advanced: Multi-Source Entity Correlation": {
        "description": "Correlating users across SigninLogs and AuditLogs with complex filtering.",
        "kql": """
let FailedSignins = SigninLogs
    | where ResultType != 0
    | summarize FailedCount = count() by UserPrincipalName, bin(TimeGenerated, 1h);
let FileDeletions = AuditLogs
    | where OperationName == "DeleteFile"
    | summarize DeletionCount = count() by UserPrincipalName = tostring(parse_json_path(RawData, 'user')), bin(TimeGenerated, 1h);
FailedSignins
| join kind=inner (FileDeletions) on UserPrincipalName, TimeGenerated
| project TimeGenerated, UserPrincipalName, FailedCount, DeletionCount
| where FailedCount > 5 and DeletionCount > 10
"""
    },
    "Advanced: Geo-Distance Anomaly": {
        "description": "High-complexity geometric/spatial logic (Simplified for SQL compatibility).",
        "kql": """
SigninLogs
| where ResultType == 0
| sort by UserPrincipalName asc, TimeGenerated asc
| extend PrevTime = prev(TimeGenerated), PrevUser = prev(UserPrincipalName)
| extend PrevCity = prev(Location)
| where UserPrincipalName == PrevUser
| extend TimeDiff = datetime_diff('hour', TimeGenerated, PrevTime)
| where TimeDiff > 0 and TimeDiff < 1
| where Location != PrevCity
| summarize SuspiciousTravelCount = count() by UserPrincipalName, Location, PrevCity
"""
    },
    "Advanced: Statistical Thresholding": {
        "description": "Using aggregations to define dynamic thresholds per user.",
        "kql": """
let Baseline = AppLogs
    | where TimeGenerated between (ago(7d) .. ago(1d))
    | summarize AvgRequests = avg(count()) by UserID, bin(TimeGenerated, 1h);
AppLogs
| where TimeGenerated > ago(1d)
| summarize CurrentRequests = count() by UserID, bin(TimeGenerated, 1h)
| join kind=inner (Baseline) on UserID, TimeGenerated
| where CurrentRequests > AvgRequests * 3
| project UserID, TimeGenerated, CurrentRequests, AvgRequests
"""
    }
}

def run_advanced_stress_tests():
    print("====================================================")
    print("KQLBridge Advanced Stress Tests - v0.8.0")
    print("Pushing Transpiler Limits with Sentinel Patterns")
    print("====================================================\n")

    for name, data in ADVANCED_TESTS.items():
        print(f"--- TEST CASE: {name} ---")
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

        # 4. Translate to T-SQL
        try:
            print("\n>>> Translating to T-SQL...")
            tsql = translate(kql, target="tsql")
            print(tsql)
        except Exception as e:
            print(f"T-SQL TRANSLATION FAILED: {type(e).__name__}: {e}")

        print("-" * 50 + "\n")

if __name__ == "__main__":
    run_advanced_stress_tests()
