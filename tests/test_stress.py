"""
test_stress.py — KQLBridge Stress & Regression Tests
====================================================
Comprehensive stress testing against real-world KQL patterns.
Tests edge cases, performance, and correctness.
"""

import pytest
from kqlbridge import translate


class TestComplexQueries:
    """Test complex real-world KQL queries."""

    def test_deeply_nested_iff_expressions(self):
        """Test multiple nested iff() function calls."""
        kql = """
        MyTable
        | extend Risk = iff(Score > 90, "Critical",
                    iff(Score > 70, "High",
                    iff(Score > 50, "Medium", "Low")))
        | project Name, Risk
        """
        result = translate(kql, target="spark")
        assert "CASE" in result
        assert "WHEN" in result
        assert result.count("WHEN") >= 3

    def test_multiple_aggregations_with_conditions(self):
        """Test summarize with multiple conditional aggregations."""
        kql = """
        Events
        | summarize 
            TotalCount=count(),
            SuccessCount=countif(Status == "success"),
            ErrorCount=countif(Status == "error"),
            AvgDuration=avgif(Duration, Status == "success")
        by Date
        """
        result = translate(kql, target="spark")
        assert "GROUP BY" in result
        assert result.count("COUNT") >= 1
        assert "CASE WHEN" in result

    def test_union_with_different_schemas(self):
        """Test union of tables with different column sets."""
        kql = """
        Table1 | project A, B, C
        | union (Table2 | project A, B, C)
        | union (Table3 | project A, B, C)
        """
        result = translate(kql, target="spark")
        assert "UNION ALL" in result
        assert result.count("UNION ALL") == 2

    def test_complex_where_with_logical_operators(self):
        """Test complex WHERE clause with AND/OR nesting."""
        kql = """
        Logs
        | where (Level == "ERROR" or Level == "CRITICAL")
            and (Timestamp > ago(1d))
            and not(Source contains "test")
        | project Message, Timestamp
        """
        result = translate(kql, target="spark")
        assert "WHERE" in result
        assert "OR" in result
        assert "AND" in result
        assert "NOT" in result

    def test_time_binning_multiple_intervals(self):
        """Test bin() with various time intervals."""
        kql = """
        TimeSeries
        | summarize Count=count() by bin(Timestamp, 1h)
        | union (TimeSeries | summarize Count=count() by bin(Timestamp, 1d))
        """
        result = translate(kql, target="spark")
        assert "DATE_TRUNC" in result or "TIMESTAMP_SECONDS" in result

    def test_extend_with_multiple_computed_columns(self):
        """Test extend with many computed column expressions."""
        kql = """
        Data
        | extend Month = bin(Timestamp, 1d)
        | extend DayOfWeek = dayofweek(Timestamp)
        | extend IsWeekend = iff(dayofweek(Timestamp) == 0 or dayofweek(Timestamp) == 6, true, false)
        | extend Risk = iff(Value > 100, "High", "Low")
        | project Timestamp, Month, DayOfWeek, IsWeekend, Risk
        """
        result = translate(kql, target="spark")
        assert "DATE_TRUNC" in result or "TIMESTAMP_SECONDS" in result
        assert "DAYOFWEEK" in result
        assert "CASE" in result

    def test_string_operations_variety(self):
        """Test various string operations."""
        kql = """
        Strings
        | extend 
            Upper = toupper(Name),
            Lower = tolower(Name),
            Length = strlen(Name),
            Starts = startswith(Name, "test"),
            Contains = contains(Name, "error")
        | where Length > 5
        """
        result = translate(kql, target="spark")
        assert "UPPER" in result
        assert "LOWER" in result
        assert "LENGTH" in result
        assert "LIKE" in result or "RLIKE" in result


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_extend(self):
        """Test extend with minimal operations."""
        kql = "T | extend X = 1"
        result = translate(kql, target="spark")
        assert "SELECT" in result
        assert "X" in result

    def test_single_column_project(self):
        """Test project with single column."""
        kql = "T | project A"
        result = translate(kql, target="spark")
        assert "SELECT" in result
        assert "A" in result

    def test_count_operator_alone(self):
        """Test count operator without other operations."""
        kql = "T | count"
        result = translate(kql, target="spark")
        assert "COUNT(*)" in result

    def test_distinct_with_columns(self):
        """Test distinct on specific columns."""
        kql = "T | distinct A, B, C"
        result = translate(kql, target="spark")
        assert "DISTINCT" in result
        assert "SELECT" in result

    def test_order_by_multiple_columns(self):
        """Test order by with multiple columns and directions."""
        kql = "T | order by A asc, B desc, C asc"
        result = translate(kql, target="spark")
        assert "ORDER BY" in result
        assert "ASC" in result or "asc" in result
        assert "DESC" in result or "desc" in result

    def test_take_with_limit(self):
        """Test take operator."""
        kql = "T | take 100"
        result = translate(kql, target="spark")
        assert "LIMIT" in result
        assert "100" in result

    def test_null_comparisons(self):
        """Test null value comparisons."""
        kql = "T | where isnull(Value) or isnotnull(Other)"
        result = translate(kql, target="spark")
        assert "IS NULL" in result or "is null" in result
        assert "IS NOT NULL" in result or "is not null" in result

    def test_in_operator_negation(self):
        """Test !in operator (not in)."""
        kql = "T | where Status !in ('deleted', 'archived')"
        result = translate(kql, target="spark")
        assert "NOT IN" in result or "not in" in result


class TestPerformanceCharacteristics:
    """Test that queries don't have pathological performance issues."""

    def test_large_summarize_many_aggregations(self):
        """Test summarize with many aggregation functions."""
        aggs = ",\n            ".join([f"Agg{i}=sum(Col{i})" for i in range(20)])
        kql = f"""
        LargeTable
        | summarize
            {aggs}
        by Category
        """
        result = translate(kql, target="spark")
        # Should complete without timeout and generate valid SQL
        assert "GROUP BY" in result
        assert "SUM" in result

    def test_deeply_nested_where_clause(self):
        """Test deeply nested where clauses."""
        conditions = " or ".join([f"Col{i} > {i}" for i in range(10)])
        kql = f"T | where {conditions}"
        result = translate(kql, target="spark")
        assert "WHERE" in result

    def test_long_project_list(self):
        """Test projection with many columns."""
        cols = ", ".join([f"Col{i}" for i in range(50)])
        kql = f"T | project {cols}"
        result = translate(kql, target="spark")
        assert "SELECT" in result


class TestTypeConversions:
    """Test type conversion functions."""

    def test_tostring_conversions(self):
        """Test tostring() function."""
        kql = "T | extend S = tostring(Value)"
        result = translate(kql, target="spark")
        assert "CAST" in result or "CAST" in result
        assert "STRING" in result or "string" in result

    def test_toint_conversions(self):
        """Test toint() function."""
        kql = "T | extend I = toint(Value)"
        result = translate(kql, target="spark")
        assert "CAST" in result
        assert "INT" in result

    def test_todouble_conversions(self):
        """Test todouble() function."""
        kql = "T | extend D = todouble(Value)"
        result = translate(kql, target="spark")
        assert "CAST" in result
        assert "DOUBLE" in result

    def test_chained_conversions(self):
        """Test multiple type conversions in sequence."""
        kql = "T | extend S = tostring(toint(Value))"
        result = translate(kql, target="spark")
        # Should have nested CAST calls
        assert result.count("CAST") >= 2


class TestDateTimeOperations:
    """Test datetime-related operations."""

    def test_datetime_literals(self):
        """Test datetime() literal syntax."""
        kql = 'T | where Timestamp > datetime(2024-01-01)'
        result = translate(kql, target="spark")
        assert "TIMESTAMP" in result or "timestamp" in result

    def test_datetime_diff(self):
        """Test datetime_diff() function."""
        kql = "T | extend Days = datetime_diff('day', Timestamp, now())"
        result = translate(kql, target="spark")
        assert "datediff" in result or "DATEDIFF" in result

    def test_datetime_add(self):
        """Test datetime_add() function."""
        kql = "T | extend Future = datetime_add('day', 30, Timestamp)"
        result = translate(kql, target="spark")
        assert "INTERVAL" in result or "interval" in result

    def test_ago_expression(self):
        """Test ago() time expression."""
        kql = "T | where Timestamp > ago(7d)"
        result = translate(kql, target="spark")
        assert "CURRENT_TIMESTAMP" in result or "current_timestamp" in result
        assert "INTERVAL" in result or "interval" in result


class TestIPv4Operations:
    """Test IPv4-specific functions."""

    def test_ipv4_is_private(self):
        """Test ipv4_is_private() function."""
        kql = "T | where ipv4_is_private(IP)"
        result = translate(kql, target="spark")
        # Should generate BETWEEN clauses for private ranges
        assert "BETWEEN" in result

    def test_ipv4_is_in_range(self):
        """Test ipv4_is_in_range() function."""
        kql = "T | where ipv4_is_in_range(IP, '192.168.0.0/16')"
        result = translate(kql, target="spark")
        assert "BETWEEN" in result


class TestJoinOperations:
    """Test join operations (if implemented)."""

    def test_inner_join_syntax(self):
        """Test basic inner join."""
        kql = """
        T1
        | join kind=inner (T2) on Key
        """
        try:
            result = translate(kql, target="spark")
            assert "JOIN" in result
            assert "ON" in result
        except NotImplementedError:
            pytest.skip("Join not yet implemented")


class TestRegression:
    """Regression tests for known issues."""

    def test_bang_in_operator(self):
        """Regression: !in operator should be properly parsed."""
        kql = "T | where Status !in ('test', 'dev')"
        result = translate(kql, target="spark")
        assert "NOT IN" in result or "not in" in result

    def test_extend_then_summarize(self):
        """Regression: extend followed by summarize should work."""
        kql = """
        T
        | extend Month = bin(Timestamp, 1d)
        | summarize Count=count() by Month
        """
        result = translate(kql, target="spark")
        assert "GROUP BY" in result

    def test_union_then_summarize(self):
        """Regression: union followed by additional operations."""
        kql = """
        T1 | project A, B
        | union (T2 | project A, B)
        | summarize Count=count() by A
        """
        result = translate(kql, target="spark")
        assert "UNION ALL" in result
        assert "GROUP BY" in result

    def test_sentinel_anomalous_login_spikes(self):
        """Test real-world Sentinel: failed login spikes per hour."""
        kql = """
        SecurityEvent
        | where TimeGenerated > ago(24h)
        | where EventID == 4625
        | summarize FailedCount = count() by Account, bin(TimeGenerated, 1h)
        | where FailedCount > 10
        | sort by FailedCount desc
        """
        result = translate(kql, target="spark")
        assert "FROM (" in result
        assert "GROUP BY" in result
        assert "WHERE FailedCount > 10" in result or "where failedcount > 10" in result.lower()
        assert "ORDER BY FailedCount DESC" in result or "order by failedcount desc" in result.lower()

    def test_sentinel_suspicious_powershell_join(self):
        """Test real-world Sentinel: suspicious powershell processes joined with network events."""
        kql = """
        let SuspiciousProcesses = DeviceProcessEvents
            | where FileName == "powershell.exe"
            | where CommandLine has_any ("encoded", "bypass", "hidden");
        SuspiciousProcesses
        | join kind=inner (
            DeviceNetworkEvents
            | where RemotePort == 4444
        ) on DeviceId
        | project TimeGenerated, DeviceName, AccountName, CommandLine, RemoteIP
        """
        result = translate(kql, target="spark")
        assert "WITH SuspiciousProcesses AS" in result or "with suspiciousprocesses as" in result.lower()
        assert "INNER JOIN (" in result or "inner join (" in result.lower()
        assert "FROM DeviceNetworkEvents" in result or "from devicenetworkevents" in result.lower()
        assert "RemotePort = 4444" in result

    def test_sentinel_multi_location_signin(self):
        """Test real-world Sentinel: multi-location login alerts."""
        kql = """
        SigninLogs
        | where TimeGenerated > ago(24h)
        | summarize LocationCount = dcount(Location) by UserPrincipalName, bin(TimeGenerated, 1h)
        | where LocationCount > 1
        """
        result = translate(kql, target="spark")
        assert "FROM (" in result
        assert "GROUP BY" in result
        assert "WHERE LocationCount > 1" in result or "where locationcount > 1" in result.lower()


class TestAdvancedThreatHuntingQueries:
    """Stress tests representing highly complex, real-world security analytics & threat-hunting queries."""

    def test_lateral_movement_and_admin_abuse(self):
        kql = """
        let ForeignLogins = SigninLogs
            | where TimeGenerated > ago(7d)
            | where Location != "US" and (ResultType == 0 or ResultType == 50126)
            | summarize FailedCount = countif(ResultType == 50126), SuccessCount = countif(ResultType == 0) by UserPrincipalName, IPAddress;
        let AdminActions = AuditLogs
            | where TimeGenerated > ago(7d)
            | where OperationName in ("Add user", "Add member to role", "Update user")
            | project TimeGenerated, OperationName, TargetUser = TargetResources, DeviceId = UserPrincipalName;
        ForeignLogins
        | join kind=inner (AdminActions) on DeviceId
        | extend HighRisk = iff(FailedCount > 5 and SuccessCount > 0, true, false)
        | where HighRisk == true
        | summarize ActionCount = count() by DeviceId, OperationName, bin(TimeGenerated, 1h)
        """
        # Test Spark SQL Translation
        spark_sql = translate(kql, target="spark")
        assert "WITH ForeignLogins AS" in spark_sql or "with foreignlogins as" in spark_sql.lower()
        assert "AdminActions AS" in spark_sql or "adminactions as" in spark_sql.lower()
        assert "INNER JOIN AdminActions" in spark_sql or "inner join adminactions" in spark_sql.lower()
        assert "CASE WHEN (FailedCount > 5 AND SuccessCount > 0) THEN true ELSE false END" in spark_sql
        assert "GROUP BY DeviceId, OperationName" in spark_sql or "group by deviceid, operationname" in spark_sql.lower()

        # Test T-SQL Translation
        tsql = translate(kql, target="tsql")
        assert "WITH ForeignLogins AS" in tsql or "with foreignlogins as" in tsql.lower()
        assert "DATEADD(day, -7, GETDATE())" in tsql
        assert "CASE WHEN (FailedCount > 5 AND SuccessCount > 0) THEN 1 ELSE 0 END" in tsql

        # Test PySpark Translation
        pyspark_df = translate(kql, target="pyspark")
        assert "ForeignLogins = spark.table('SigninLogs')" in pyspark_df
        assert "ForeignLogins = ForeignLogins.filter(\"(Location <> 'US' AND (ResultType = 0 OR ResultType = 50126))\")" in pyspark_df
        assert "df = ForeignLogins" in pyspark_df
        assert "join_right_DeviceId = AdminActions" in pyspark_df
        assert "HighRisk" in pyspark_df

    def test_port_scan_lolbin_correlation(self):
        kql = """
        let ObfuscatedCommands = DeviceProcessEvents
            | where TimeGenerated > ago(1d)
            | where FileName =~ "powershell.exe" or FileName =~ "cmd.exe"
            | where CommandLine has "bypass" or CommandLine has "encodedcommand" or CommandLine has "downloadstring"
            | project ProcessTime = TimeGenerated, DeviceId, CommandLine;
        let PortScans = DeviceNetworkEvents
            | where TimeGenerated > ago(1d)
            | where RemotePort in (4444, 8080, 9000)
            | summarize ConnectionCount = count() by DeviceId, RemotePort, bin(TimeGenerated, 10m);
        ObfuscatedCommands
        | join kind=inner (PortScans) on DeviceId
        | where ProcessTime between (TimeGenerated .. datetime_add("minute", 30, TimeGenerated))
        | summarize AlertCount = count() by DeviceId, RemotePort
        """
        # Test Spark SQL
        spark_sql = translate(kql, target="spark")
        assert "LOWER(FileName) = LOWER('powershell.exe') OR LOWER(FileName) = LOWER('cmd.exe')" in spark_sql
        assert "CommandLine RLIKE '(?i)\\\\bbypass\\\\b'" in spark_sql or "CommandLine LIKE '%bypass%'" in spark_sql
        assert "RemotePort IN (4444, 8080, 9000)" in spark_sql
        assert "ProcessTime >= TimeGenerated" in spark_sql

        # Test T-SQL
        tsql = translate(kql, target="tsql")
        assert "DATEADD(day, -1, GETDATE())" in tsql
        assert "RemotePort IN (4444, 8080, 9000)" in tsql

        # Test PySpark
        pyspark_df = translate(kql, target="pyspark")
        assert "ObfuscatedCommands = spark.table('DeviceProcessEvents')" in pyspark_df

    def test_ransomware_killchain_tracking(self):
        kql = """
        let Downloads = DeviceFileEvents
            | where TimeGenerated > ago(3d)
            | where FolderPath has "Downloads" and (FileName endswith ".exe" or FileName endswith ".ps1" or FileName endswith ".bat")
            | project DownloadTime = TimeGenerated, DeviceId, DownloadedFile = FileName;
        let Evasion = SecurityEvent
            | where TimeGenerated > ago(3d)
            | where EventID == 1102 or EventID == 4698 or EventID == 4702
            | project EvasionTime = TimeGenerated, DeviceId = Computer, EventID;
        let Exfil = DeviceNetworkEvents
            | where TimeGenerated > ago(3d)
            | where BytesSent > 10000000
            | summarize TotalExfilBytes = sum(BytesSent) by DeviceId;
        Downloads
        | join kind=inner (Evasion) on DeviceId
        | join kind=inner (Exfil) on DeviceId
        | where EvasionTime > DownloadTime
        | project DeviceId, DownloadedFile, EventID, TotalExfilBytes
        """
        # Test Spark SQL
        spark_sql = translate(kql, target="spark")
        assert "Downloads AS (" in spark_sql
        assert "Evasion AS (" in spark_sql
        assert "Exfil AS (" in spark_sql
        assert "SUM(BytesSent) AS TotalExfilBytes" in spark_sql or "sum(BytesSent) AS TotalExfilBytes" in spark_sql.lower()
        assert "INNER JOIN Evasion" in spark_sql or "inner join evasion" in spark_sql.lower()
        assert "INNER JOIN Exfil" in spark_sql or "inner join exfil" in spark_sql.lower()
        assert "EvasionTime > DownloadTime" in spark_sql

        # Test T-SQL
        tsql = translate(kql, target="tsql")
        assert "DATEADD(day, -3, GETDATE())" in tsql

        # Test PySpark
        pyspark_df = translate(kql, target="pyspark")
        assert "Downloads = spark.table('DeviceFileEvents')" in pyspark_df
        assert "df = Downloads" in pyspark_df

    def test_login_anomaly_statistical_hunter(self):
        kql = """
        SigninLogs
        | where TimeGenerated > ago(30d)
        | where ResultType == 0
        | extend Duration = toint(Duration)
        | summarize 
            TotalLogins = count(),
            AvgDuration = avg(Duration),
            P95Duration = percentile(Duration, 95),
            UniqueLocations = dcount(Location),
            AccessedHosts = make_list(ResourceDisplayName)
          by UserPrincipalName, bin(TimeGenerated, 1d)
        | where UniqueLocations > 3 or AvgDuration > P95Duration
        | sort by UniqueLocations desc
        """
        # Test Spark SQL
        spark_sql = translate(kql, target="spark")
        assert "CAST(Duration AS INT) AS Duration" in spark_sql
        assert "COUNT(*) AS TotalLogins" in spark_sql or "count(*) AS TotalLogins" in spark_sql.lower()
        assert "AVG(Duration) AS AvgDuration" in spark_sql or "avg(Duration) AS AvgDuration" in spark_sql.lower()
        assert "approx_percentile(Duration, 0.95) AS P95Duration" in spark_sql
        assert "COUNT(DISTINCT Location) AS UniqueLocations" in spark_sql or "count(DISTINCT Location) AS UniqueLocations" in spark_sql.lower()
        assert "collect_list(ResourceDisplayName) AS AccessedHosts" in spark_sql
        assert "ORDER BY UniqueLocations DESC" in spark_sql or "order by uniquelocations desc" in spark_sql.lower()

        # Test T-SQL
        tsql = translate(kql, target="tsql")
        assert "CAST(Duration AS INT) AS Duration" in tsql
        assert "DATEADD(day, -30, GETDATE())" in tsql

        # Test PySpark
        pyspark_df = translate(kql, target="pyspark")
        assert "df = spark.table('SigninLogs')" in pyspark_df
        assert 'F.expr("approx_percentile(Duration, 0.95) AS P95Duration")' in pyspark_df
        assert 'F.expr("collect_list(ResourceDisplayName) AS AccessedHosts")' in pyspark_df


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
