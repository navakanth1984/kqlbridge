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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
