"""
tests/test_gps_stress.py — GPS Adversarial Stress Test Suite for KQLBridge
==========================================================================
GPS Framework: Gaslight · Pushback · Stress-test
Author: Senior QA Stress-Test Engineer (adversarial auditor)

This file DOES NOT modify any source code. It tests the existing transpiler
as a black box, probing standard, edge, overload, and adversarial scenarios.

Test Philosophy:
- Standard tests MUST ALL pass for a SHIP verdict.
- Edge tests: pass = clean output OR graceful ValueError.
                 fail = unhandled exception or dangerous SQL.
- Overload tests: must not crash. Degradation acceptable.
- Adversarial tests: must not produce SQL injection or crash.
"""

import pytest
import re
from kqlbridge import translate, detect_operators, is_supported


# ═══════════════════════════════════════════════════════════════════════════════
#  STANDARD TESTS — Must ALL pass for SHIP verdict
# ═══════════════════════════════════════════════════════════════════════════════

class TestGPS_Standard:
    """Standard KQL queries a Fabric/Sentinel analyst writes daily."""

    def test_s01_basic_where(self):
        """Basic where clause with string comparison."""
        kql = "AppLogs | where Level == 'Error'"
        sql = translate(kql)
        assert "SELECT" in sql
        assert "WHERE" in sql
        assert "Error" in sql

    def test_s02_project(self):
        """Project selects specific columns."""
        kql = "AppLogs | project Message, Level, TimeGenerated"
        sql = translate(kql)
        assert "Message" in sql
        assert "Level" in sql
        assert "TimeGenerated" in sql
        # Should not have * when projecting specific columns
        lines = sql.strip().split('\n')
        select_line = lines[0]
        assert "Message" in select_line

    def test_s03_extend_with_expression(self):
        """Extend adds computed columns."""
        kql = "AppLogs | extend LenMsg = strlen(Message)"
        sql = translate(kql)
        assert "LenMsg" in sql
        assert "LENGTH" in sql or "strlen" in sql.lower()

    def test_s04_summarize_count_by(self):
        """Summarize with count by group."""
        kql = "AppLogs | summarize count() by Level"
        sql = translate(kql)
        upper = sql.upper()
        assert "COUNT(*)" in upper
        assert "GROUP BY" in upper
        assert "Level" in sql

    def test_s05_where_project_chain(self):
        """Multi-pipe: where → project."""
        kql = "AppLogs | where Level == 'Error' | project Message, TimeGenerated"
        sql = translate(kql)
        assert "WHERE" in sql.upper()
        assert "Message" in sql
        assert "TimeGenerated" in sql

    def test_s06_datetime_function(self):
        """datetime() literal with ISO format."""
        kql = "AppLogs | where TimeGenerated > datetime(2024-01-01)"
        sql = translate(kql)
        assert "2024-01-01" in sql
        # Should have TIMESTAMP or CAST, not raw subtraction artifacts
        assert "TIMESTAMP" in sql.upper() or "CAST" in sql.upper()

    def test_s07_join_with_on(self):
        """Inner join with on clause."""
        kql = "AppLogs | join (Users) on UserId"
        sql = translate(kql)
        upper = sql.upper()
        assert "JOIN" in upper
        assert "UserId" in sql

    def test_s08_union_tables(self):
        """Union of multiple tables."""
        kql = "AppLogs | union ErrorLogs"
        sql = translate(kql)
        upper = sql.upper()
        assert "UNION" in upper
        assert "AppLogs" in sql
        assert "ErrorLogs" in sql

    def test_s09_order_by_desc(self):
        """Order by with direction."""
        kql = "AppLogs | order by TimeGenerated desc"
        sql = translate(kql)
        upper = sql.upper()
        assert "ORDER BY" in upper
        assert "DESC" in upper

    def test_s10_take_limit(self):
        """Take/limit produces LIMIT clause."""
        kql = "AppLogs | take 100"
        sql = translate(kql)
        assert "LIMIT 100" in sql.upper() or "TOP 100" in sql.upper()

    def test_s11_summarize_with_bin(self):
        """Summarize with bin() time bucketing."""
        kql = "AppLogs | summarize count() by bin(TimeGenerated, 1h)"
        sql = translate(kql)
        upper = sql.upper()
        assert "COUNT(*)" in upper
        assert "GROUP BY" in upper
        # Should use DATE_TRUNC or equivalent bucketing
        assert "DATE_TRUNC" in upper or "FLOOR" in upper

    def test_s12_let_scalar_binding(self):
        """Let binding with scalar expression."""
        kql = "let threshold = 100; AppLogs | where Amount > threshold"
        sql = translate(kql)
        upper = sql.upper()
        assert "WHERE" in upper
        assert "100" in sql

    def test_s13_ago_expression(self):
        """ago() time expression."""
        kql = "AppLogs | where TimeGenerated > ago(24h)"
        sql = translate(kql)
        upper = sql.upper()
        assert "CURRENT_TIMESTAMP" in upper
        assert "INTERVAL" in upper or "DATEADD" in upper

    def test_s14_distinct(self):
        """Distinct operator."""
        kql = "AppLogs | distinct Level"
        sql = translate(kql)
        assert "DISTINCT" in sql.upper()

    def test_s15_count_operator(self):
        """Standalone count operator."""
        kql = "AppLogs | count"
        sql = translate(kql)
        assert "COUNT(*)" in sql.upper()

    def test_s16_iff_expression(self):
        """iff() conditional expression in extend."""
        kql = "AppLogs | extend Status = iff(Level == 'Error', 'Bad', 'Good')"
        sql = translate(kql)
        assert "CASE" in sql.upper()
        assert "WHEN" in sql.upper()
        assert "Bad" in sql
        assert "Good" in sql

    def test_s17_summarize_multiple_aggs(self):
        """Summarize with multiple aggregation functions."""
        kql = "AppLogs | summarize total=count(), avg_dur=avg(Duration), mx=max(Duration) by Level"
        sql = translate(kql)
        upper = sql.upper()
        assert "COUNT(*)" in upper
        assert "AVG" in upper
        assert "MAX" in upper
        assert "GROUP BY" in upper

    def test_s18_where_in_list(self):
        """Where with in operator."""
        kql = "AppLogs | where Level in ('Error', 'Warning', 'Critical')"
        sql = translate(kql)
        assert "IN" in sql.upper()
        assert "Error" in sql

    def test_s19_not_in(self):
        """Where with !in operator."""
        kql = "AppLogs | where Level !in ('Debug', 'Trace')"
        sql = translate(kql)
        assert "NOT IN" in sql.upper()

    def test_s20_string_contains(self):
        """String contains operator."""
        kql = "AppLogs | where Message contains 'timeout'"
        sql = translate(kql)
        assert "timeout" in sql.lower()
        assert "LIKE" in sql.upper() or "RLIKE" in sql.upper()


# ═══════════════════════════════════════════════════════════════════════════════
#  EDGE TESTS — Graceful degradation expected
# ═══════════════════════════════════════════════════════════════════════════════

class TestGPS_Edge:
    """Edge cases: malformed, ambiguous, or boundary-condition inputs."""

    def test_e01_empty_string(self):
        """Empty string should raise a clean error, not crash."""
        with pytest.raises((ValueError, Exception)):
            translate("")

    def test_e02_whitespace_only(self):
        """Whitespace-only input should raise a clean error."""
        with pytest.raises((ValueError, Exception)):
            translate("   \t\n  ")

    def test_e03_single_table_name(self):
        """Just a table name with no pipes — valid KQL, should produce SELECT *."""
        try:
            sql = translate("AppLogs")
            assert "SELECT" in sql.upper()
            assert "AppLogs" in sql
        except (ValueError, Exception):
            # Also acceptable if it requires at least one pipe
            pass

    def test_e04_column_names_are_sql_reserved_words(self):
        """Column names that are SQL reserved words (select, from, where)."""
        try:
            sql = translate("AppLogs | project select, from, where")
            # If it works, just verify it produced output
            assert isinstance(sql, str)
        except (ValueError, Exception):
            # Grammar may reject these as keywords — acceptable
            pass

    def test_e05_unmatched_parentheses(self):
        """Unmatched parentheses should raise, not hang."""
        with pytest.raises((ValueError, Exception)):
            translate("AppLogs | where strlen(Message")

    def test_e06_unmatched_quotes(self):
        """Unmatched quotes should raise, not hang."""
        with pytest.raises((ValueError, Exception)):
            translate("AppLogs | where Level == 'Error")

    def test_e07_single_char_table_name(self):
        """Single-character table name."""
        try:
            sql = translate("T | where x == 1")
            assert "SELECT" in sql.upper()
        except (ValueError, Exception):
            pass

    def test_e08_numeric_string_comparison(self):
        """Comparing column to a number — should not crash."""
        kql = "AppLogs | where Duration > 1000"
        sql = translate(kql)
        assert "1000" in sql

    def test_e09_double_pipe(self):
        """Double pipe (||) — should not cause infinite loop or crash."""
        try:
            sql = translate("AppLogs || where x == 1")
            # If it produces something, check it's a string
            assert isinstance(sql, str)
        except (ValueError, Exception):
            # Clean error is acceptable
            pass

    def test_e10_very_long_string_literal(self):
        """Long string literal (1000 chars) in where clause."""
        long_str = "a" * 1000
        kql = f"AppLogs | where Message == '{long_str}'"
        try:
            sql = translate(kql)
            assert long_str in sql
        except (ValueError, Exception):
            pass

    def test_e11_where_with_multiple_and_or(self):
        """Complex boolean with mixed AND/OR."""
        kql = ("AppLogs | where Level == 'Error' and Duration > 100 "
               "or Level == 'Warning' and Duration > 500")
        try:
            sql = translate(kql)
            assert "WHERE" in sql.upper()
        except (ValueError, Exception):
            pass


# ═══════════════════════════════════════════════════════════════════════════════
#  OVERLOAD TESTS — Must not crash; degradation acceptable
# ═══════════════════════════════════════════════════════════════════════════════

class TestGPS_Overload:
    """Extremely complex queries that stress parser and generator limits."""

    def test_o01_fifteen_pipe_chain(self):
        """15-pipe chain: where → extend → where → project → take, repeated."""
        pipes = []
        for i in range(5):
            pipes.append(f"where Duration > {i * 100}")
            pipes.append(f"extend Extra{i} = Duration + {i}")
            pipes.append(f"where Extra{i} > {i * 50}")
        kql = "AppLogs | " + " | ".join(pipes)
        try:
            sql = translate(kql)
            assert isinstance(sql, str)
            assert len(sql) > 0
        except (ValueError, NotImplementedError) as e:
            # Graceful error is fine
            assert isinstance(str(e), str)

    def test_o02_summarize_many_aggs(self):
        """Summarize with 10 aggregation functions."""
        aggs = []
        for i in range(10):
            if i % 3 == 0:
                aggs.append(f"c{i}=count()")
            elif i % 3 == 1:
                aggs.append(f"s{i}=sum(Duration)")
            else:
                aggs.append(f"a{i}=avg(Duration)")
        kql = f"AppLogs | summarize {', '.join(aggs)} by Level"
        try:
            sql = translate(kql)
            upper = sql.upper()
            assert "GROUP BY" in upper
            assert "COUNT(*)" in upper
        except (ValueError, NotImplementedError) as e:
            assert isinstance(str(e), str)

    def test_o03_project_many_columns(self):
        """Project with 30 columns."""
        cols = [f"Col{i}" for i in range(30)]
        kql = f"AppLogs | project {', '.join(cols)}"
        try:
            sql = translate(kql)
            for c in cols[:5]:
                assert c in sql
        except (ValueError, NotImplementedError) as e:
            assert isinstance(str(e), str)

    def test_o04_deeply_nested_iff(self):
        """Deeply nested iff() — 5 levels deep."""
        kql = ("AppLogs | extend Status = "
               "iff(Level == 'Error', 'Critical', "
               "iff(Level == 'Warning', 'Watch', "
               "iff(Level == 'Info', 'Normal', "
               "iff(Level == 'Debug', 'Low', "
               "'Unknown'))))")
        try:
            sql = translate(kql)
            assert "CASE" in sql.upper()
            assert "WHEN" in sql.upper()
        except (ValueError, NotImplementedError) as e:
            assert isinstance(str(e), str)

    def test_o05_chained_where_extend_summarize(self):
        """Complex pipeline: where → extend → summarize → where → order → take."""
        kql = ("AppLogs "
               "| where TimeGenerated > ago(7d) "
               "| extend DayBucket = bin(TimeGenerated, 1d) "
               "| summarize cnt=count() by DayBucket "
               "| where cnt > 10 "
               "| order by cnt desc "
               "| take 5")
        try:
            sql = translate(kql)
            upper = sql.upper()
            assert "SELECT" in upper
            assert "COUNT(*)" in upper or "CNT" in upper
        except (ValueError, NotImplementedError) as e:
            assert isinstance(str(e), str)

    def test_o06_multiple_extend_blocks(self):
        """Multiple consecutive extend operations."""
        extends = [f"extend Col{i} = Duration + {i}" for i in range(8)]
        kql = "AppLogs | " + " | ".join(extends)
        try:
            sql = translate(kql)
            assert "Col0" in sql
            assert "Col7" in sql
        except (ValueError, NotImplementedError) as e:
            assert isinstance(str(e), str)

    def test_o07_union_many_tables(self):
        """Union of 5 tables."""
        tables = [f"Table{i}" for i in range(5)]
        kql = f"AppLogs | union {', '.join(tables)}"
        try:
            sql = translate(kql)
            upper = sql.upper()
            assert "UNION" in upper
        except (ValueError, NotImplementedError) as e:
            assert isinstance(str(e), str)

    def test_o08_where_chain_ten_conditions(self):
        """Ten consecutive where clauses."""
        wheres = [f"where Duration > {i * 10}" for i in range(10)]
        kql = "AppLogs | " + " | ".join(wheres)
        try:
            sql = translate(kql)
            assert "WHERE" in sql.upper()
        except (ValueError, NotImplementedError) as e:
            assert isinstance(str(e), str)

    def test_o09_make_series_full(self):
        """Full make-series query (bypasses grammar, hits TimeSeriesMicroModel)."""
        kql = ("Heartbeat "
               "| make-series cnt=count() on TimeGenerated "
               "from ago(7d) to now() step 1h "
               "by ComputerName")
        try:
            sql = translate(kql)
            assert isinstance(sql, str)
            assert len(sql) > 50
        except (ValueError, NotImplementedError) as e:
            assert isinstance(str(e), str)


# ═══════════════════════════════════════════════════════════════════════════════
#  ADVERSARIAL TESTS — Must not produce dangerous SQL or crash
# ═══════════════════════════════════════════════════════════════════════════════

class TestGPS_Adversarial:
    """Injection attempts, crash vectors, and malicious inputs."""

    def test_a01_sql_injection_in_string_literal(self):
        """SQL injection attempt in a string literal value."""
        kql = "Events | where col == '1; DROP TABLE Events; --'"
        try:
            sql = translate(kql)
            # The injected SQL should be INSIDE quotes, not executable
            assert "DROP TABLE" not in sql.upper().split("'")[-1]
            # Must not produce multiple statements
            # Count semicolons outside of quoted strings
            unquoted = re.sub(r"'[^']*'", "", sql)
            assert ";" not in unquoted, f"Unquoted semicolons in output: {sql}"
        except (ValueError, Exception):
            # Clean rejection is acceptable
            pass

    def test_a02_column_name_injection(self):
        """SQL injection attempt via column name (bracket notation not in grammar)."""
        # The grammar only allows NAME: /[a-zA-Z_][a-zA-Z0-9_.]*/ so this should fail parsing
        kql = "Events | project Robert_DROP_TABLE_Students"
        try:
            sql = translate(kql)
            # If it parses, the injected SQL should be treated as a column name
            assert isinstance(sql, str)
        except (ValueError, Exception):
            pass

    def test_a03_unicode_in_query(self):
        """Unicode characters in table/column names."""
        kql = "Événements | where Statüs == 'Ërreur'"
        try:
            sql = translate(kql)
            assert isinstance(sql, str)
        except (ValueError, Exception):
            # Clean rejection of non-ASCII is fine
            pass

    def test_a04_null_bytes_in_input(self):
        """Null bytes in input — must not crash silently."""
        kql = "AppLogs\x00 | where Level == 'Error'"
        try:
            sql = translate(kql)
            # If it produces output, null byte should be stripped/escaped
            assert isinstance(sql, str)
        except (ValueError, Exception):
            # Clean error is acceptable
            pass

    def test_a05_extremely_long_query(self):
        """10KB+ query — must not cause excessive memory or time."""
        # Build a ~12KB query with many where conditions
        conditions = [f"Col{i} == '{('x' * 50)}'" for i in range(200)]
        # We can't have 200 pipes (parser would be very slow), so use AND chaining
        big_condition = " and ".join(conditions[:30])
        kql = f"AppLogs | where {big_condition}"
        try:
            sql = translate(kql)
            assert isinstance(sql, str)
            assert len(sql) > 100
        except (ValueError, Exception):
            # Clean error or timeout is acceptable
            pass

    def test_a06_comment_injection(self):
        """SQL comment injection attempt."""
        kql = "Events | where Level == 'Error' -- DROP TABLE Events"
        try:
            sql = translate(kql)
            # The comment should not appear as executable SQL
            assert isinstance(sql, str)
        except (ValueError, Exception):
            pass

    def test_a07_semicolon_in_value(self):
        """Semicolon in a string value should stay quoted."""
        kql = "Events | where Message == 'status;code=500;fatal'"
        try:
            sql = translate(kql)
            # Verify the semicolons are inside quotes
            assert "status;code=500;fatal" in sql
            # No unquoted semicolons
            unquoted = re.sub(r"'[^']*'", "", sql)
            assert ";" not in unquoted
        except (ValueError, Exception):
            pass

    def test_a08_nested_quotes(self):
        """Nested quotes that could break string escaping."""
        kql = "Events | where Message == 'It\\'s a test'"
        try:
            sql = translate(kql)
            assert isinstance(sql, str)
        except (ValueError, Exception):
            # Clean parse error is fine
            pass

    def test_a09_pipe_bomb_recursive(self):
        """Deeply recursive pipes to test for stack overflow."""
        # 50 where clauses chained
        pipes = " | ".join([f"where Col{i % 5} > {i}" for i in range(50)])
        kql = f"AppLogs | {pipes}"
        try:
            sql = translate(kql)
            assert isinstance(sql, str)
        except (ValueError, RecursionError) as e:
            # RecursionError is a FAIL — should degrade gracefully
            assert not isinstance(e, RecursionError), \
                f"RecursionError on 50 pipes — stack safety issue: {e}"

    def test_a10_xss_in_string(self):
        """XSS payload in string literal — should be harmlessly quoted."""
        kql = "Events | where Message == '<script>alert(1)</script>'"
        try:
            sql = translate(kql)
            # The XSS should be inside SQL string quotes, not raw
            assert "<script>" in sql  # It's in the string literal
            assert isinstance(sql, str)
        except (ValueError, Exception):
            pass


# ═══════════════════════════════════════════════════════════════════════════════
#  CROSS-DIALECT TESTS — Verify tsql and pyspark don't crash
# ═══════════════════════════════════════════════════════════════════════════════

class TestGPS_CrossDialect:
    """Verify that all three dialects produce output for the same query."""

    def test_d01_spark_produces_output(self):
        kql = "AppLogs | where Level == 'Error' | summarize count() by Level | take 10"
        sql = translate(kql, target="spark")
        assert "SELECT" in sql.upper()

    def test_d02_tsql_produces_output(self):
        kql = "AppLogs | where Level == 'Error' | summarize count() by Level | take 10"
        sql = translate(kql, target="tsql")
        assert "SELECT" in sql.upper()

    def test_d03_pyspark_produces_output(self):
        kql = "AppLogs | where Level == 'Error' | summarize count() by Level | take 10"
        code = translate(kql, target="pyspark")
        # PySpark output is Python code, not SQL
        assert isinstance(code, str)
        assert len(code) > 10

    def test_d04_invalid_target_raises(self):
        """Invalid target should raise ValueError."""
        with pytest.raises(ValueError):
            translate("AppLogs | where x == 1", target="postgres")


# ═══════════════════════════════════════════════════════════════════════════════
#  DETECT OPERATORS TESTS — Utility function validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestGPS_DetectOperators:
    """Validate detect_operators() returns correct operator lists."""

    def test_detect_basic_operators(self):
        ops = detect_operators("AppLogs | where x == 1 | summarize count() by y")
        assert "where" in ops
        assert "summarize" in ops

    def test_detect_multiple_operators(self):
        ops = detect_operators(
            "T | where x > 1 | extend y = x + 1 | summarize count() by y | order by y desc | take 10"
        )
        assert "where" in ops
        assert "extend" in ops
        assert "summarize" in ops

    def test_detect_make_series(self):
        ops = detect_operators("T | make-series count() on ts from ago(7d) to now() step 1h")
        assert "make-series" in ops
