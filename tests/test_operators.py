"""
test_operators.py — Per-Operator Unit Tests
============================================
Unit tests for each of the 14 v0.1 KQL operators.

These are NOT the locked eval benchmark — they are development aids.
Run with: pytest tests/test_operators.py -v

Unlike prepare.py:
- These tests may be modified as the implementation evolves
- They use a simpler equality check (no canonical form)
- They're meant for fast TDD cycles during BIT Build phase
"""

import pytest
from kqlbridge import translate, detect_operators, is_supported


# ─── Helpers ────────────────────────────────────────────────────────────────

def sql(kql: str) -> str:
    """Shorthand: translate KQL → Spark SQL."""
    return translate(kql, target="spark")


def lines(kql: str) -> list[str]:
    """Split result into non-empty lines for structural checks."""
    return [line.strip() for line in sql(kql).splitlines() if line.strip()]


# ─── 01 where ───────────────────────────────────────────────────────────────

class TestWhere:
    def test_basic_equality(self):
        result = sql("AppLogs | where Level == 'Error'")
        assert "WHERE Level = 'Error'" in result

    def test_not_equal(self):
        result = sql("AppLogs | where Level != 'Debug'")
        assert "WHERE Level <> 'Debug'" in result

    def test_greater_than(self):
        result = sql("AppLogs | where Duration > 500")
        assert "WHERE Duration > 500" in result

    def test_and_condition(self):
        result = sql("AppLogs | where Level == 'Error' and Region == 'east'")
        assert "AND" in result
        assert "Level = 'Error'" in result

    def test_or_condition(self):
        result = sql("AppLogs | where Level == 'Error' or Level == 'Warning'")
        assert "OR" in result

    def test_contains(self):
        result = sql("AppLogs | where Message contains 'timeout'")
        assert "LIKE '%timeout%'" in result

    def test_has(self):
        result = sql("AppLogs | where Message has 'timeout'")
        assert "RLIKE '(?i)\\\\btimeout\\\\b'" in result

    def test_case_insensitive_equality(self):
        result = sql("AppLogs | where Level =~ 'Error'")
        assert "LOWER(Level) = LOWER('Error')" in result

    def test_startswith(self):
        result = sql("AppLogs | where Host startswith 'web'")
        assert "LIKE 'web%'" in result

    def test_in_list(self):
        result = sql("AppLogs | where Level in ('Error', 'Warning')")
        assert "IN ('Error', 'Warning')" in result

    def test_not_in_list(self):
        result = sql("AppLogs | where Level !in ('Debug', 'Info')")
        assert "NOT IN ('Debug', 'Info')" in result

    def test_isnotnull(self):
        result = sql("AppLogs | where isnotnull(UserId)")
        assert "UserId IS NOT NULL" in result

    def test_isnull(self):
        result = sql("AppLogs | where isnull(Region)")
        assert "Region IS NULL" in result

    def test_chained_where(self):
        result = sql("AppLogs | where Level == 'Error' | where Duration > 500")
        assert "WHERE" in result
        assert "Level = 'Error'" in result
        assert "Duration > 500" in result


# ─── 02 project ─────────────────────────────────────────────────────────────

class TestProject:
    def test_single_column(self):
        result = sql("AppLogs | project Message")
        assert result.startswith("SELECT Message")

    def test_multiple_columns(self):
        result = sql("AppLogs | project Message, Level, ServiceName")
        assert "SELECT Message, Level, ServiceName" in result

    def test_from_clause_preserved(self):
        result = sql("AppLogs | project Message")
        assert "FROM AppLogs" in result


# ─── 03 + 04 summarize ───────────────────────────────────────────────────────

class TestSummarize:
    def test_count_by(self):
        result = sql("AppLogs | summarize count() by ServiceName")
        assert "COUNT(*)" in result
        assert "GROUP BY ServiceName" in result
        assert "SELECT ServiceName" in result

    def test_sum_by(self):
        result = sql("Orders | summarize total = sum(Amount) by Region")
        assert "SUM(Amount) AS total" in result
        assert "GROUP BY Region" in result

    def test_avg_by(self):
        result = sql("Orders | summarize avg_val = avg(Amount) by Region")
        assert "AVG(Amount) AS avg_val" in result

    def test_min_by(self):
        result = sql("AppLogs | summarize min_dur = min(Duration) by Level")
        assert "MIN(Duration) AS min_dur" in result

    def test_max_by(self):
        result = sql("AppLogs | summarize max_dur = max(Duration) by Level")
        assert "MAX(Duration) AS max_dur" in result

    def test_no_group_by(self):
        result = sql("AppLogs | summarize count()")
        assert "COUNT(*)" in result
        assert "GROUP BY" not in result

    def test_multiple_aggregations(self):
        result = sql("Orders | summarize cnt = count(), total = sum(Amount) by Region")
        assert "COUNT(*) AS cnt" in result
        assert "SUM(Amount) AS total" in result

    def test_multiple_group_by_cols(self):
        result = sql("AppLogs | summarize count() by Level, ServiceName")
        assert "GROUP BY Level, ServiceName" in result

    def test_dcount(self):
        result = sql("AppLogs | summarize unique_users = dcount(UserId)")
        assert "COUNT(DISTINCT UserId) AS unique_users" in result


# ─── 05 bin ──────────────────────────────────────────────────────────────────

class TestBin:
    def test_bin_hour(self):
        result = sql("AppLogs | summarize count() by bin(TimeGenerated, 1h)")
        assert "DATE_TRUNC('hour', TimeGenerated)" in result

    def test_bin_day(self):
        result = sql("AppLogs | summarize count() by bin(TimeGenerated, 1d)")
        assert "DATE_TRUNC('day', TimeGenerated)" in result

    def test_bin_minute_single(self):
        result = sql("AppLogs | summarize count() by bin(TimeGenerated, 1m)")
        assert "DATE_TRUNC('minute', TimeGenerated)" in result

    def test_bin_5m_floor_logic(self):
        result = sql("AppLogs | summarize count() by bin(TimeGenerated, 5m)")
        assert "FLOOR" in result
        assert "300" in result  # 5 * 60

    def test_bin_auto(self):
        from kqlbridge import translate
        kql = "AppLogs | summarize count() by bin_auto(TimeGenerated)"
        res_spark = translate(kql, target="spark")
        assert "DATE_TRUNC('day', TimeGenerated)" in res_spark

        res_tsql = translate(kql, target="tsql")
        assert "DATEADD(day, DATEDIFF(day, 0, TimeGenerated), 0)" in res_tsql


# ─── 06 ago ──────────────────────────────────────────────────────────────────

class TestAgo:
    def test_ago_hours(self):
        result = sql("AppLogs | where TimeGenerated > ago(24h)")
        assert "INTERVAL '24 hours'" in result
        assert "CURRENT_TIMESTAMP" in result

    def test_ago_days(self):
        result = sql("AppLogs | where TimeGenerated > ago(7d)")
        assert "INTERVAL '7 days'" in result

    def test_ago_minutes(self):
        result = sql("AppLogs | where TimeGenerated > ago(30m)")
        assert "INTERVAL '30 minutes'" in result


# ─── 07 extend ───────────────────────────────────────────────────────────────

class TestExtend:
    def test_extend_literal(self):
        result = sql("AppLogs | extend ErrorCode = 500")
        assert "500 AS ErrorCode" in result

    def test_extend_function(self):
        result = sql("AppLogs | extend MsgUpper = toupper(Message)")
        assert "UPPER(Message) AS MsgUpper" in result

    def test_extend_preserves_star(self):
        result = sql("AppLogs | extend X = 1")
        assert "SELECT *" in result

    def test_extend_two_columns(self):
        result = sql("AppLogs | extend A = 1, B = 2")
        assert "1 AS A" in result
        assert "2 AS B" in result


# ─── 08 order by / sort by ───────────────────────────────────────────────────

class TestOrder:
    def test_order_by_desc(self):
        result = sql("AppLogs | order by TimeGenerated desc")
        assert "ORDER BY TimeGenerated DESC" in result

    def test_sort_by_alias(self):
        result = sql("AppLogs | sort by Level asc")
        assert "ORDER BY Level ASC" in result

    def test_multiple_order_cols(self):
        result = sql("AppLogs | order by Level asc, TimeGenerated desc")
        assert "Level ASC, TimeGenerated DESC" in result

    def test_default_direction_is_asc(self):
        result = sql("AppLogs | order by Level")
        assert "ORDER BY Level ASC" in result


# ─── 09 take / limit ─────────────────────────────────────────────────────────

class TestTake:
    def test_take_keyword(self):
        result = sql("AppLogs | take 100")
        assert "LIMIT 100" in result

    def test_limit_keyword(self):
        result = sql("AppLogs | limit 50")
        assert "LIMIT 50" in result


# ─── 10 distinct ─────────────────────────────────────────────────────────────

class TestDistinct:
    def test_distinct_single(self):
        result = sql("AppLogs | distinct Level")
        assert "SELECT DISTINCT Level" in result

    def test_distinct_multiple(self):
        result = sql("AppLogs | distinct Level, ServiceName")
        assert "SELECT DISTINCT Level, ServiceName" in result

    def test_distinct_star(self):
        result = sql("AppLogs | distinct *")
        assert "SELECT DISTINCT *" in result


# ─── 11 join ─────────────────────────────────────────────────────────────────

class TestJoin:
    def test_inner_join_default(self):
        result = sql("AppLogs | join (Users) on UserId")
        assert "INNER JOIN Users" in result
        assert "AppLogs.UserId = Users.UserId" in result

    def test_leftouter_join(self):
        result = sql("AppLogs | join kind=leftouter (Users) on UserId")
        assert "LEFT OUTER JOIN Users" in result

    def test_join_multiple_keys(self):
        result = sql("Orders | join (Customers) on CustomerId, Region")
        assert "CustomerId" in result
        assert "Region" in result

    def test_chained_joins(self):
        result = sql("Table1 | join kind=inner (Table2) on x | join kind=leftouter (Table3) on y")
        assert "INNER JOIN Table2 ON Table1.x = Table2.x" in result
        assert "LEFT OUTER JOIN Table3 ON Table1.y = Table3.y" in result

    def test_union_join_pipeline(self):
        result = sql("Table1 | union Table2 | join (Table3) on x")
        assert "FROM (\nSELECT * FROM Table1\nUNION ALL\nSELECT * FROM Table2\n) _union_result" in result
        assert "INNER JOIN Table3 ON _union_result.x = Table3.x" in result


# ─── 12 union ────────────────────────────────────────────────────────────────

class TestUnion:
    def test_union_two_tables(self):
        result = sql("AppLogs | union ErrorLogs")
        assert "UNION ALL" in result
        assert "SELECT * FROM AppLogs" in result
        assert "SELECT * FROM ErrorLogs" in result

    def test_union_three_tables(self):
        result = sql("T1 | union T2, T3")
        assert result.count("UNION ALL") == 2


# ─── 13 let ──────────────────────────────────────────────────────────────────

class TestLet:
    def test_single_let(self):
        kql = "let errors = AppLogs | where Level == 'Error'; errors | summarize count() by ServiceName"
        result = sql(kql)
        assert "WITH errors AS" in result
        assert "CTE" not in result  # no accidental prose

    def test_let_used_as_table(self):
        kql = "let errors = AppLogs | where Level == 'Error'; errors | summarize count() by ServiceName"
        result = sql(kql)
        assert "FROM errors" in result

    def test_scalar_let_binding_spark(self):
        from kqlbridge import translate
        kql = "let x = ago(1d); Table1 | where Time > x"
        res = translate(kql, target="spark")
        assert "WHERE Time > CURRENT_TIMESTAMP - INTERVAL '1 days'" in res
        assert "WITH" not in res

    def test_scalar_let_binding_tsql(self):
        from kqlbridge import translate
        kql = "let x = ago(1d); Table1 | where Time > x"
        res = translate(kql, target="tsql")
        assert "WHERE Time > DATEADD(day, -1, GETDATE())" in res
        assert "WITH" not in res

    def test_scalar_let_binding_pyspark(self):
        from kqlbridge.generators.pyspark import PySparkGenerator
        from kqlbridge.parser import parse
        kql = "let x = ago(1d); Table1 | where Time > x"
        res = PySparkGenerator().generate(parse(kql))
        assert 'df = df.filter("Time > CURRENT_TIMESTAMP - INTERVAL \'1 days\'")' in res
        assert "WITH" not in res

    def test_multi_line_let_chaining(self):
        from kqlbridge import translate
        kql = "let lookback = ago(7d); let threshold = lookback; AppLogs | where TimeGenerated > threshold"
        res = translate(kql, target="spark")
        assert "WHERE TimeGenerated > CURRENT_TIMESTAMP - INTERVAL '7 days'" in res
        assert "WITH" not in res

        res_tsql = translate(kql, target="tsql")
        assert "WHERE TimeGenerated > DATEADD(day, -7, GETDATE())" in res_tsql
        assert "WITH" not in res_tsql


# ─── 14 count ────────────────────────────────────────────────────────────────

class TestCount:
    def test_count_only(self):
        result = sql("AppLogs | count")
        assert "COUNT(*) AS count_" in result

    def test_where_then_count(self):
        result = sql("AppLogs | where Level == 'Error' | count")
        assert "COUNT(*) AS count_" in result
        assert "WHERE Level = 'Error'" in result


# ─── API Tests ───────────────────────────────────────────────────────────────

class TestPublicAPI:
    def test_detect_operators(self):
        ops = detect_operators("AppLogs | where x == 1 | summarize count() by y")
        assert "where" in ops
        assert "summarize" in ops

    def test_is_supported_basic(self):
        assert is_supported("AppLogs | where Level == 'Error'") is True

    def test_translate_returns_string(self):
        result = translate("AppLogs", target="spark")
        assert isinstance(result, str)
        assert len(result) > 0


# ─── Community Functions ─────────────────────────────────────────────────────

class TestCommunityFunctions:
    def test_datetime_quotes(self):
        spark_res = translate("AppLogs | where TimeGenerated > datetime('2024-01-01')", target="spark")
        tsql_res = translate("AppLogs | where TimeGenerated > datetime('2024-01-01')", target="tsql")
        assert "TIMESTAMP '2024-01-01'" in spark_res
        assert "CAST('2024-01-01' AS DATETIME2)" in tsql_res

        spark_res_double = translate("AppLogs | where TimeGenerated > datetime(\"2024-01-01\")", target="spark")
        tsql_res_double = translate("AppLogs | where TimeGenerated > datetime(\"2024-01-01\")", target="tsql")
        assert "TIMESTAMP '2024-01-01'" in spark_res_double
        assert "CAST('2024-01-01' AS DATETIME2)" in tsql_res_double

    def test_coalesce(self):
        spark_res = translate("AppLogs | extend x = coalesce(A, B, C)", target="spark")
        tsql_res = translate("AppLogs | extend x = coalesce(A, B, C)", target="tsql")
        assert "COALESCE(A, B, C)" in spark_res
        assert "COALESCE(A, B, C)" in tsql_res

    def test_split(self):
        spark_res = translate("AppLogs | extend parts = split(Message, ',')", target="spark")
        tsql_res = translate("AppLogs | extend parts = split(Message, ',')", target="tsql")
        assert "split(Message, ',')" in spark_res
        assert "STRING_SPLIT(Message, ',')" in tsql_res

    def test_datetime_add(self):
        spark_res = translate("AppLogs | extend next_day = datetime_add('day', 1, TimeGenerated)", target="spark")
        tsql_res = translate("AppLogs | extend next_day = datetime_add('day', 1, TimeGenerated)", target="tsql")
        assert "(TimeGenerated + (1 * INTERVAL '1' DAY))" in spark_res
        assert "DATEADD(day, 1, TimeGenerated)" in tsql_res

    def test_datetime_diff(self):
        spark_res = translate("AppLogs | extend diff = datetime_diff('day', dt1, dt2)", target="spark")
        tsql_res = translate("AppLogs | extend diff = datetime_diff('day', dt1, dt2)", target="tsql")
        assert "datediff(dt1, dt2)" in spark_res
        assert "DATEDIFF(day, dt2, dt1)" in tsql_res

    def test_strcat_delim(self):
        spark_res = translate("AppLogs | extend full = strcat_delim('-', A, B)", target="spark")
        tsql_res = translate("AppLogs | extend full = strcat_delim('-', A, B)", target="tsql")
        assert "concat_ws('-', A, B)" in spark_res
        assert "CONCAT_WS('-', A, B)" in tsql_res


class TestV07Features:
    def test_serialize_and_prev(self):
        # Test serialize operator and prev() function
        kql = "AppLogs | serialize | extend prev_level = prev(Level)"
        spark_res = translate(kql, target="spark")
        tsql_res = translate(kql, target="tsql")
        assert "LAG(Level) OVER (ORDER BY (SELECT NULL))" in spark_res
        assert "LAG(Level) OVER (ORDER BY (SELECT NULL))" in tsql_res

    def test_has_any(self):
        # Test has_any operator
        kql = "AppLogs | where Message has_any ('timeout', 'error')"
        spark_res = translate(kql, target="spark")
        tsql_res = translate(kql, target="tsql")
        assert "(Message RLIKE '(?i)\\\\btimeout\\\\b' OR Message RLIKE '(?i)\\\\berror\\\\b')" in spark_res
        assert "(Message LIKE '%timeout%' OR Message LIKE '%error%')" in tsql_res

    def test_percentile(self):
        # Test percentile aggregate function
        kql = "AppLogs | summarize percentile(Duration, 95) by Host"
        spark_res = translate(kql, target="spark")
        tsql_res = translate(kql, target="tsql")
        assert "approx_percentile(Duration, 0.95)" in spark_res
        assert "PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY Duration)" in tsql_res

    def test_make_list(self):
        # Test make_list aggregate function
        kql = "AppLogs | summarize make_list(Level) by Host"
        spark_res = translate(kql, target="spark")
        tsql_res = translate(kql, target="tsql")
        assert "collect_list(Level)" in spark_res
        assert "STRING_AGG(Level, ',')" in tsql_res

    def test_soc_threat_hunting_functions(self):
        # 1. parse_json_path
        kql_json = "AppLogs | extend val = parse_json(col).field"
        spark_json = translate(kql_json, target="spark")
        tsql_json = translate(kql_json, target="tsql")
        assert "get_json_object(col, '$.field')" in spark_json
        assert "JSON_VALUE(col, '$.field')" in tsql_json

        # 2. mv_expand
        kql_mvexpand = "AppLogs | mv-expand col"
        spark_mvexpand = translate(kql_mvexpand, target="spark")
        tsql_mvexpand = translate(kql_mvexpand, target="tsql")
        assert "LATERAL VIEW explode(col)" in spark_mvexpand
        assert "CROSS APPLY OPENJSON(col)" in tsql_mvexpand

        # 3. case
        kql_case = "AppLogs | extend x = case(c1, v1, c2, v2, d)"
        spark_case = translate(kql_case, target="spark")
        tsql_case = translate(kql_case, target="tsql")
        assert "CASE WHEN c1 THEN v1 WHEN c2 THEN v2 ELSE d END" in spark_case
        assert "CASE WHEN c1 THEN v1 WHEN c2 THEN v2 ELSE d END" in tsql_case

        # 4. ipv4_is_private
        kql_private = "AppLogs | where ipv4_is_private(ip)"
        spark_private = translate(kql_private, target="spark")
        tsql_private = translate(kql_private, target="tsql")
        assert "BETWEEN 167772160 AND 184549375" in spark_private
        assert "BETWEEN 167772160 AND 184549375" in tsql_private

        # 5. ipv4_is_in_range
        kql_range = "AppLogs | where ipv4_is_in_range(ip, '192.168.1.0/24')"
        spark_range = translate(kql_range, target="spark")
        tsql_range = translate(kql_range, target="tsql")
        assert "BETWEEN 3232235776 AND 3232236031" in spark_range
        assert "BETWEEN 3232235776 AND 3232236031" in tsql_range

    def test_soc_threat_hunting_pyspark(self):
        from kqlbridge.generators.pyspark import PySparkGenerator
        from kqlbridge.parser import parse

        # 1. parse_json
        kql_json = "AppLogs | extend val = parse_json(col).field"
        res_json = PySparkGenerator().generate(parse(kql_json))
        assert 'df = df.selectExpr("*", "get_json_object(col, \'$.field\') AS val")' in res_json

        # 2. case
        kql_case = "AppLogs | extend x = case(c1, v1, c2, v2, d)"
        res_case = PySparkGenerator().generate(parse(kql_case))
        assert 'df = df.selectExpr("*", "CASE WHEN c1 THEN v1 WHEN c2 THEN v2 ELSE d END AS x")' in res_case

        # 3. ipv4_is_private — verify BETWEEN ranges rendered without '= true' suffix
        kql_private = "AppLogs | where ipv4_is_private(ip)"
        res_private = PySparkGenerator().generate(parse(kql_private))
        assert "BETWEEN 167772160 AND 184549375" in res_private  # 10.0.0.0/8
        assert "BETWEEN 2886729728 AND 2887778303" in res_private  # 172.16.0.0/12
        assert "= true" not in res_private  # no redundant bool suffix on FuncCall


class TestV08Features:
    def test_casting_functions(self):
        # Test tostring, toint, tolong, todouble across targets
        kql = "AppLogs | extend s = tostring(c1), i = toint(c2), l = tolong(c3), d = todouble(c4)"
        
        # 1. Spark SQL
        spark = translate(kql, target="spark")
        assert "CAST(c1 AS STRING)" in spark
        assert "CAST(c2 AS INT)" in spark
        assert "CAST(c3 AS BIGINT)" in spark
        assert "CAST(c4 AS DOUBLE)" in spark

        # 2. T-SQL
        tsql = translate(kql, target="tsql")
        assert "CAST(c1 AS NVARCHAR(MAX))" in tsql
        assert "CAST(c2 AS INT)" in tsql
        assert "CAST(c3 AS BIGINT)" in tsql
        assert "CAST(c4 AS FLOAT)" in tsql

    def test_format_datetime(self):
        kql = "AppLogs | extend formatted = format_datetime(timestamp, 'yyyy-MM-dd')"
        
        # 1. Spark SQL
        spark = translate(kql, target="spark")
        assert "DATE_FORMAT(timestamp, 'yyyy-MM-dd')" in spark

        # 2. T-SQL
        tsql = translate(kql, target="tsql")
        assert "FORMAT(timestamp, 'yyyy-MM-dd')" in tsql

    def test_array_functions(self):
        # Test array_length and array_index_of
        kql_len = "AppLogs | extend len = array_length(arr)"
        kql_idx = "AppLogs | extend idx = array_index_of(arr, 'target')"

        # 1. Spark SQL
        spark_len = translate(kql_len, target="spark")
        spark_idx = translate(kql_idx, target="spark")
        assert "size(arr)" in spark_len
        assert "array_position(arr, 'target')" in spark_idx

        # 2. T-SQL
        tsql_len = translate(kql_len, target="tsql")
        tsql_idx = translate(kql_idx, target="tsql")
        assert "COALESCE((SELECT COUNT(*) FROM OPENJSON(arr)), 0)" in tsql_len
        assert "COALESCE((SELECT MIN(CAST([key] AS INT)) FROM OPENJSON(arr) WHERE [value] = 'target'), -1)" in tsql_idx

    def test_case_insensitive_list_membership(self):
        # 1. Literal set membership
        kql_lit = "AppLogs | where Message in~ ('Error', 'Warning') and Message !in~ ('info')"
        
        spark_lit = translate(kql_lit, target="spark")
        assert "LOWER(Message) IN (LOWER('Error'), LOWER('Warning'))" in spark_lit
        assert "LOWER(Message) NOT IN (LOWER('info'))" in spark_lit

        tsql_lit = translate(kql_lit, target="tsql")
        assert "LOWER(Message) IN (LOWER('Error'), LOWER('Warning'))" in tsql_lit
        assert "LOWER(Message) NOT IN (LOWER('info'))" in tsql_lit

        # 2. Subquery membership
        kql_sub = "AppLogs | where Message in~ (OtherTable | project Name) and Message !in~ (OtherTable | project Name)"
        
        spark_sub = translate(kql_sub, target="spark").replace("\n", " ")
        while "  " in spark_sub:
            spark_sub = spark_sub.replace("  ", " ")
        assert "LOWER(Message) IN (SELECT LOWER(x) FROM (SELECT Name FROM OtherTable) AS _ci_sub(x))" in spark_sub
        assert "LOWER(Message) NOT IN (SELECT LOWER(x) FROM (SELECT Name FROM OtherTable) AS _ci_sub(x))" in spark_sub

        tsql_sub = translate(kql_sub, target="tsql").replace("\n", " ")
        while "  " in tsql_sub:
            tsql_sub = tsql_sub.replace("  ", " ")
        assert "LOWER(Message) IN (SELECT LOWER(x) FROM (SELECT Name FROM OtherTable) AS _ci_sub(x))" in tsql_sub
        assert "LOWER(Message) NOT IN (SELECT LOWER(x) FROM (SELECT Name FROM OtherTable) AS _ci_sub(x))" in tsql_sub


class TestV09PySpark:
    def test_pyspark_integration_translate(self):
        from kqlbridge import translate
        kql = "AppLogs | where Level == 'Error' | project TimeGenerated, Message"
        res = translate(kql, target="pyspark")
        assert "import pyspark.sql.functions as F" in res
        assert "df = spark.table('AppLogs')" in res
        assert "df = df.filter(\"Level = 'Error'\")" in res
        assert 'df = df.selectExpr("TimeGenerated", "Message")' in res

    def test_explain_pyspark(self):
        from kqlbridge.explain import explain
        kql = "AppLogs | where Level == 'Error' | project TimeGenerated, Message"
        res = explain(kql, target="pyspark")
        assert "# KQLBridge Translation Annotations" in res.annotated_sql
        assert "#  1. where col == val" in res.annotated_sql
        assert "df = spark.table('AppLogs')" in res.annotated_sql

    def test_cli_pyspark_translate(self):
        from kqlbridge.cli import _translate
        import argparse
        import io
        from contextlib import redirect_stdout
        
        args = argparse.Namespace(kql="AppLogs | take 5", pyspark=True, tsql=False)
        f = io.StringIO()
        with redirect_stdout(f):
            code = _translate(args)
        assert code == 0
        out = f.getvalue()
        assert "df = df.limit(5)" in out

    def test_cli_pyspark_explain(self):
        from kqlbridge.cli import _explain
        import argparse
        import io
        from contextlib import redirect_stdout
        
        args = argparse.Namespace(kql="AppLogs | take 5", pyspark=True, tsql=False)
        f = io.StringIO()
        with redirect_stdout(f):
            code = _explain(args)
        assert code == 0
        out = f.getvalue()
        assert "# KQLBridge Translation Annotations" in out
        assert "df = df.limit(5)" in out


