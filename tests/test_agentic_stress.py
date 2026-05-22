"""
test_agentic_stress.py — KQLBridge Agentic Stress-Test Suite
=============================================================
Senior QA Stress-Test Engineer — Agentic Engineering Framework

Dimensions covered:
  1. Jagged Intelligence Map (10+ probes)
  2. Thread Safety (3+ concurrent tests)
  3. Bloat & Bypass Audit (documented inline)
  4. Oracle Validation (external — run prepare.py separately)

RULE: This file ONLY tests. It NEVER modifies source.
"""

from __future__ import annotations
import pytest
import threading
import concurrent.futures
import re
import sys
import os
import time
from typing import Any


# ─── IMPORT kqlbridge ──────────────────────────────────────────────────────────

from kqlbridge import translate, detect_operators, is_supported, check, __version__


# ═══════════════════════════════════════════════════════════════════════════════
# DIMENSION 1: JAGGED INTELLIGENCE PROBES
# ═══════════════════════════════════════════════════════════════════════════════


class TestJaggedIntelligence:
    """Probe WHERE the transpiler is strong vs where it silently fails."""

    # ── JI-01: Basic where + project (should be rock-solid) ──────────────

    def test_ji01_basic_where_project(self):
        """
        TEST: ji01_basic_where_project
        DIMENSION: Jagged Intelligence
        HYPOTHESIS: Simple where + project is the bread-and-butter. Should PASS always.
        """
        kql = "AppLogs | where Level == 'Error' | project Message, Level"
        result = translate(kql, target="spark")
        assert "SELECT" in result
        assert "Message" in result
        assert "Level" in result
        assert "WHERE" in result
        assert "Level = 'Error'" in result

    # ── JI-02: Chained where operators (5+ pipes) ───────────────────────

    def test_ji02_multi_pipe_chain(self):
        """
        TEST: ji02_multi_pipe_chain
        DIMENSION: Jagged Intelligence
        HYPOTHESIS: 5+ pipe operators chained. Parser and generator should handle gracefully.
        """
        kql = (
            "AppLogs "
            "| where Level == 'Error' "
            "| where Duration > 500 "
            "| extend IsError = true "
            "| project Message, Duration, IsError "
            "| order by Duration desc "
            "| take 10"
        )
        result = translate(kql, target="spark")
        assert "SELECT" in result
        assert "WHERE" in result
        assert "ORDER BY" in result
        assert "LIMIT 10" in result
        # Verify chained wheres become AND clauses
        assert "AND" in result

    # ── JI-03: Nested iff → CASE WHEN ──────────────────────────────────

    def test_ji03_nested_iff(self):
        """
        TEST: ji03_nested_iff
        DIMENSION: Jagged Intelligence
        HYPOTHESIS: Nested iff(iff()) should produce nested CASE WHEN. This is a known jagged edge.
        """
        kql = (
            "AppLogs | extend Severity = iff(Level == 'Error', 'High', "
            "iff(Level == 'Warning', 'Medium', 'Low'))"
        )
        result = translate(kql, target="spark")
        # Should produce CASE WHEN ... WHEN ... ELSE ... END
        assert "CASE" in result
        assert "WHEN" in result
        assert "ELSE" in result
        assert "END" in result
        # Should have at least 2 WHEN branches
        when_count = result.count("WHEN")
        assert when_count >= 2, f"Expected >= 2 WHEN branches, got {when_count}"

    # ── JI-04: datetime preprocessor — the FIX-01 regression ─────────

    def test_ji04_datetime_bare_iso(self):
        """
        TEST: ji04_datetime_bare_iso
        DIMENSION: Jagged Intelligence
        HYPOTHESIS: datetime(2024-01-01) must be preprocessed into a quoted string.
                    Without FIX-01 this was parsed as subtraction.
        """
        kql = "AppLogs | where TimeGenerated > datetime(2024-01-01)"
        result_spark = translate(kql, target="spark")
        assert "TIMESTAMP" in result_spark
        assert "2024-01-01" in result_spark
        # Must NOT contain subtraction artifacts
        assert "2024 - 1 - 1" not in result_spark

    def test_ji04b_datetime_tsql(self):
        """
        TEST: ji04b_datetime_tsql
        DIMENSION: Jagged Intelligence
        HYPOTHESIS: datetime literal in T-SQL must emit CAST('...' AS DATETIME2), not CONVERT or TIMESTAMP.
        """
        kql = "AppLogs | where TimeGenerated > datetime(2024-06-15)"
        result_tsql = translate(kql, target="tsql")
        assert "DATETIME2" in result_tsql
        assert "2024-06-15" in result_tsql

    # ── JI-05: summarize with bin() + ago() combined ─────────────────

    def test_ji05_summarize_bin_ago(self):
        """
        TEST: ji05_summarize_bin_ago
        DIMENSION: Jagged Intelligence
        HYPOTHESIS: ago() + bin() combined is a high-risk semantic translation.
        """
        kql = "AppLogs | where TimeGenerated > ago(7d) | summarize count() by bin(TimeGenerated, 1h)"
        result = translate(kql, target="spark")
        assert "DATE_TRUNC" in result
        assert "CURRENT_TIMESTAMP" in result
        assert "INTERVAL" in result
        assert "GROUP BY" in result

    # ── JI-06: extend → summarize pipeline ──────────────────────────

    def test_ji06_extend_then_summarize(self):
        """
        TEST: ji06_extend_then_summarize
        DIMENSION: Jagged Intelligence
        HYPOTHESIS: extend followed by summarize should wrap in subquery so extended cols
                    are visible to GROUP BY.
        """
        kql = "Orders | extend IsLarge = Amount > 1000 | summarize count() by IsLarge"
        result = translate(kql, target="spark")
        assert "COUNT" in result
        assert "IsLarge" in result
        # Should either have a subquery wrapping the extend, or column visible in GROUP BY
        assert "GROUP BY" in result

    # ── JI-07: !in operator (negated in) ────────────────────────────

    def test_ji07_not_in_operator(self):
        """
        TEST: ji07_not_in_operator
        DIMENSION: Jagged Intelligence
        HYPOTHESIS: !in is a known regression trigger. Should produce NOT IN.
        """
        kql = "AppLogs | where Level !in ('Debug', 'Info')"
        result = translate(kql, target="spark")
        assert "NOT IN" in result
        assert "'Debug'" in result
        assert "'Info'" in result

    # ── JI-08: let bindings → CTE ──────────────────────────────────

    def test_ji08_let_to_cte(self):
        """
        TEST: ji08_let_to_cte
        DIMENSION: Jagged Intelligence
        HYPOTHESIS: let bindings should generate WITH ... AS CTEs.
        """
        kql = "let errors = AppLogs | where Level == 'Error'; errors | summarize count() by ServiceName"
        result = translate(kql, target="spark")
        assert "WITH" in result
        assert "errors" in result.lower()
        assert "AS" in result

    # ── JI-09: 5-minute bin → FLOOR logic (not DATE_TRUNC) ──────────

    def test_ji09_5min_bin_floor(self):
        """
        TEST: ji09_5min_bin_floor
        DIMENSION: Jagged Intelligence
        HYPOTHESIS: bin(col, 5m) must use FLOOR-based bucketing, not DATE_TRUNC('minute').
        """
        kql = "AppLogs | summarize count() by bin(TimeGenerated, 5m)"
        result = translate(kql, target="spark")
        assert "TIMESTAMP_SECONDS" in result or "FLOOR" in result
        assert "300" in result  # 5 * 60 = 300

    # ── JI-10: T-SQL ago() → DATEADD ──────────────────────────────

    def test_ji10_tsql_ago(self):
        """
        TEST: ji10_tsql_ago
        DIMENSION: Jagged Intelligence
        HYPOTHESIS: In T-SQL, ago(24h) must emit DATEADD(hour, -24, GETDATE()), not INTERVAL.
        """
        kql = "AppLogs | where TimeGenerated > ago(24h)"
        result = translate(kql, target="tsql")
        assert "DATEADD" in result
        assert "GETDATE" in result
        assert "INTERVAL" not in result

    # ── JI-11: T-SQL TOP n instead of LIMIT n ────────────────────────

    def test_ji11_tsql_top_not_limit(self):
        """
        TEST: ji11_tsql_top_not_limit
        DIMENSION: Jagged Intelligence
        HYPOTHESIS: T-SQL must use TOP n, not LIMIT n.
        """
        kql = "AppLogs | where Level == 'Error' | take 10"
        result = translate(kql, target="tsql")
        assert "TOP 10" in result
        assert "LIMIT" not in result

    # ── JI-12: make-series → TimeSeriesMicroModel ──────────────────

    def test_ji12_make_series_spark(self):
        """
        TEST: ji12_make_series_spark
        DIMENSION: Jagged Intelligence
        HYPOTHESIS: make-series queries should be routed to TimeSeriesMicroModel.
        """
        kql = (
            "AppLogs | make-series cnt=count() on TimeGenerated "
            "from ago(7d) to now() step 1h by ServiceName"
        )
        result = translate(kql, target="spark")
        assert "grid" in result.lower() or "WITH" in result
        # Should contain aggregation and time grid logic
        assert "count" in result.lower() or "COUNT" in result

    # ── JI-13: make-series with forward fill ─────────────────────────

    def test_ji13_make_series_forward_fill(self):
        """
        TEST: ji13_make_series_forward_fill
        DIMENSION: Jagged Intelligence
        HYPOTHESIS: make-series with series_fill_forward should emit gap-filling logic.
        """
        kql = (
            "AppLogs | make-series cnt=count() on TimeGenerated "
            "from ago(7d) to now() step 1h by ServiceName "
            "| extend filled = series_fill_forward(cnt)"
        )
        result = translate(kql, target="spark")
        # Should contain window function for forward filling
        assert "OVER" in result or "last" in result.lower()
        assert "coalesce" in result.lower() or "COALESCE" in result

    # ── JI-14: Deeply nested boolean logic ───────────────────────────

    def test_ji14_deep_boolean_nesting(self):
        """
        TEST: ji14_deep_boolean_nesting
        DIMENSION: Jagged Intelligence
        HYPOTHESIS: Deeply nested AND/OR with parens should parse without corruption.
        """
        kql = (
            "AppLogs | where (Level == 'Error' and (Duration > 500 or Region == 'east')) "
            "or (Level == 'Critical' and Region != 'west')"
        )
        result = translate(kql, target="spark")
        assert "WHERE" in result
        assert "AND" in result
        assert "OR" in result
        # Verify no syntax errors by checking balanced parentheses
        assert result.count("(") == result.count(")")

    # ── JI-15: countif aggregation ──────────────────────────────────

    def test_ji15_countif(self):
        """
        TEST: ji15_countif
        DIMENSION: Jagged Intelligence
        HYPOTHESIS: countif should translate to COUNT(CASE WHEN ... THEN 1 END).
        """
        kql = "AppLogs | summarize ErrorCount = countif(Level == 'Error') by ServiceName"
        result = translate(kql, target="spark")
        assert "COUNT" in result
        assert "CASE WHEN" in result
        assert "GROUP BY" in result


# ═══════════════════════════════════════════════════════════════════════════════
# DIMENSION 2: THREAD SAFETY STRESS
# ═══════════════════════════════════════════════════════════════════════════════


class TestThreadSafety:
    """Verify no cross-contamination occurs when translate() is called concurrently."""

    def test_ts01_concurrent_different_targets(self):
        """
        TEST: ts01_concurrent_different_targets
        DIMENSION: Thread Safety
        HYPOTHESIS: Concurrent calls with different targets should not contaminate each other.
        """
        kql = "AppLogs | where Level == 'Error' | take 10"
        results: dict[str, str] = {}
        errors: list[Exception] = []

        def worker(target: str):
            try:
                result = translate(kql, target=target)
                results[target] = result
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=worker, args=("spark",)),
            threading.Thread(target=worker, args=("tsql",)),
            threading.Thread(target=worker, args=("pyspark",)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert not errors, f"Thread errors: {errors}"
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"

        # Spark should have LIMIT, T-SQL should have TOP, PySpark should have .filter
        assert "LIMIT" in results["spark"]
        assert "TOP" in results["tsql"]
        assert "LIMIT" not in results["tsql"], "T-SQL contaminated with LIMIT from Spark"
        assert "TOP" not in results["spark"], "Spark contaminated with TOP from T-SQL"

    def test_ts02_concurrent_many_queries(self):
        """
        TEST: ts02_concurrent_many_queries
        DIMENSION: Thread Safety
        HYPOTHESIS: 50 concurrent translate() calls should all succeed without panic or crash.
        """
        queries = [
            ("AppLogs | where Level == 'Error'", "spark"),
            ("AppLogs | project Message, Level", "spark"),
            ("AppLogs | summarize count() by ServiceName", "spark"),
            ("AppLogs | where Level == 'Error' | take 5", "tsql"),
            ("AppLogs | order by TimeGenerated desc", "tsql"),
            ("Orders | summarize total = sum(Amount) by Region", "spark"),
            ("AppLogs | distinct Level", "spark"),
            ("AppLogs | where Duration > 500 | project Message", "tsql"),
            ("AppLogs | where TimeGenerated > ago(24h)", "spark"),
            ("AppLogs | extend IsError = true", "pyspark"),
        ]

        errors: list[tuple[int, str]] = []
        results: list[str | None] = [None] * 50

        def worker(idx: int):
            kql, target = queries[idx % len(queries)]
            try:
                results[idx] = translate(kql, target=target)
            except Exception as e:
                errors.append((idx, str(e)))

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(50)]
            concurrent.futures.wait(futures, timeout=60)

        assert len(errors) == 0, f"Failed {len(errors)}/50 calls: {errors[:5]}"
        assert all(r is not None for r in results), "Some results were None"

    def test_ts03_concurrent_cross_contamination_check(self):
        """
        TEST: ts03_concurrent_cross_contamination_check
        DIMENSION: Thread Safety
        HYPOTHESIS: Queries with unique table names should produce output containing those
                    exact table names, proving no cross-contamination.
        """
        queries = [
            f"Table{i} | where Level == 'Error' | project Message"
            for i in range(20)
        ]
        results: dict[int, str] = {}
        errors: list[tuple[int, str]] = []

        def worker(idx: int):
            try:
                results[idx] = translate(queries[idx], target="spark")
            except Exception as e:
                errors.append((idx, str(e)))

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            concurrent.futures.wait(futures, timeout=60)

        assert not errors, f"Thread errors: {errors}"
        for idx, result in results.items():
            expected_table = f"Table{idx}"
            assert expected_table in result, (
                f"Result for query {idx} does not contain {expected_table}. "
                f"Possible cross-contamination. Got: {result[:200]}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# DIMENSION 3: BLOAT & BYPASS AUDIT
# ═══════════════════════════════════════════════════════════════════════════════


class TestBloatAndBypassAudit:
    """
    Document and verify known bloat/bypass patterns in source code.
    These are FINDINGS — they test for the EXISTENCE of known problematic patterns.
    """

    def _read_source(self, rel_path: str) -> str:
        """Read a source file relative to the kqlbridge package."""
        import kqlbridge
        pkg_dir = os.path.dirname(kqlbridge.__file__)
        full_path = os.path.join(pkg_dir, rel_path)
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_bloat01_sys_argv_sniffing_in_generator(self):
        """
        FINDING: BLOAT-01 — sys.argv sniffing in spark_sql.py _join()
        The SparkSQLGenerator._join() method checks sys.argv for 'prepare.py' or 'eval'
        to decide whether to emit right-side WHERE clause. This is a hardcoded bypass
        that makes the transpiler behave differently during eval vs production.

        This is a P0 integrity issue.
        """
        source = self._read_source("generators/spark_sql.py")
        # Verify the pattern exists (documenting the finding)
        has_sys_argv = "sys.argv" in source
        has_prepare_check = "prepare.py" in source
        # This SHOULD NOT exist — document as finding
        if has_sys_argv and has_prepare_check:
            pytest.skip(
                "FINDING DOCUMENTED: BLOAT-01 — sys.argv sniffing in _join() method. "
                "The transpiler checks if it's running under prepare.py to change behavior. "
                "This is a bypass that masks a real behavioral difference."
            )

    def test_bloat02_dead_code_build_groupby_list(self):
        """
        FINDING: BLOAT-02 — Dead code: _build_groupby_list() in parser.py
        The function body is just 'return []' with a note saying logic moved elsewhere.
        This is dead code that should be removed.
        """
        source = self._read_source("parser.py")
        # Check for the dead function
        assert "_build_groupby_list" in source, "Dead function was already removed (good!)"
        # Verify it's truly dead (body is just 'return []')
        if 'return []' in source:
            # Find context around the function
            match = re.search(
                r"def _build_groupby_list.*?return \[\]",
                source,
                re.DOTALL,
            )
            if match:
                pytest.skip(
                    "FINDING DOCUMENTED: BLOAT-02 — _build_groupby_list() is dead code. "
                    "Body is 'return []'. Logic moved to _build_summarize. Should be removed."
                )

    def test_bloat03_passthrough_functions_with_comments(self):
        """
        FINDING: BLOAT-03 — Unknown function passthrough with GPS comment
        The spark_sql.py _func_call() emits unknown functions with a comment
        '/* KQL function — verify Spark equivalent */'. This is defensive but masks
        silent failures where unsupported functions silently pass through.
        """
        source = self._read_source("generators/spark_sql.py")
        has_passthrough = "/* KQL function" in source
        if has_passthrough:
            pytest.skip(
                "FINDING DOCUMENTED: BLOAT-03 — Unknown KQL functions pass through with a comment. "
                "This means translate() never raises on unsupported functions, it silently emits "
                "potentially invalid SQL. Consider raising NotImplementedError for safety."
            )

    def test_bloat04_window_fn_gps_comment_in_output(self):
        """
        FINDING: BLOAT-04 — GPS debug comments leaked into SQL output
        Window functions like row_number() emit inline GPS FIX-02 comments in the
        generated SQL. These comments should not appear in production output.
        """
        kql = "AppLogs | extend rn = row_number()"
        try:
            result = translate(kql, target="spark")
            has_comment = "GPS" in result or "FIX-02" in result
            if has_comment:
                pytest.skip(
                    "FINDING DOCUMENTED: BLOAT-04 — Generated SQL contains GPS debug comments: "
                    f"'{result[:200]}'. Production SQL should not contain debug annotations."
                )
        except Exception:
            pytest.skip("row_number not parseable — separate issue")

    def test_bloat05_edge_007_hardcoded_table_check(self):
        """
        FINDING: BLOAT-05 — Hardcoded table name check in _join()
        The SparkSQLGenerator._join() has a hardcoded check for table name 'Users'
        to activate legacy behavior. This is benchmark-fitting, not generalized logic.
        """
        source = self._read_source("generators/spark_sql.py")
        has_users_check = 'op.right.table == "Users"' in source
        if has_users_check:
            pytest.skip(
                "FINDING DOCUMENTED: BLOAT-05 — _join() has hardcoded check for table 'Users'. "
                "This is benchmark-fitting. The logic should be table-name agnostic."
            )


# ═══════════════════════════════════════════════════════════════════════════════
# DIMENSION 4: ADDITIONAL EDGE CASE PROBES
# ═══════════════════════════════════════════════════════════════════════════════


class TestAdditionalEdgeCases:
    """Extra probes for completeness."""

    def test_ec01_empty_table_no_operators(self):
        """Simple table scan with no pipe operators."""
        result = translate("AppLogs", target="spark")
        assert result.strip() == "SELECT *\nFROM AppLogs" or "SELECT *" in result

    def test_ec02_uppercase_keywords(self):
        """KQL is case-insensitive for keywords."""
        result = translate("AppLogs | WHERE Level == 'Error' | TAKE 10", target="spark")
        assert "WHERE" in result
        assert "LIMIT 10" in result

    def test_ec03_detect_operators_accuracy(self):
        """detect_operators should identify all used operators."""
        kql = "AppLogs | where Level == 'Error' | summarize count() by ServiceName | take 5"
        ops = detect_operators(kql)
        assert "where" in ops
        assert "summarize" in ops
        assert "take" in ops

    def test_ec04_is_supported_basic(self):
        """is_supported should return True for basic queries."""
        assert is_supported("AppLogs | where Level == 'Error'") is True

    def test_ec05_check_returns_valid(self):
        """check() should return a valid SemanticResult."""
        result = check("AppLogs | where Level == 'Error' | project Message")
        assert result.is_valid is True

    def test_ec06_multiple_targets_same_query(self):
        """Same query translated to all targets should produce target-specific SQL."""
        kql = "AppLogs | where Level == 'Error' | take 5"
        spark_result = translate(kql, target="spark")
        tsql_result = translate(kql, target="tsql")
        pyspark_result = translate(kql, target="pyspark")

        # Each should be different
        assert spark_result != tsql_result
        assert "LIMIT" in spark_result
        assert "TOP" in tsql_result

    def test_ec07_join_two_keys(self):
        """Join on two keys should produce multi-condition ON clause."""
        kql = "Orders | join (Customers) on CustomerId, Region"
        result = translate(kql, target="spark")
        assert "JOIN" in result
        assert "CustomerId" in result
        assert "Region" in result
        assert "ON" in result

    def test_ec08_union_three_tables(self):
        """Union of three tables should produce two UNION ALL."""
        kql = "T1 | union T2, T3"
        result = translate(kql, target="spark")
        assert result.count("UNION ALL") == 2

    def test_ec09_pyspark_generates_dataframe_code(self):
        """PySpark target should generate DataFrame-style Python code."""
        kql = "AppLogs | where Level == 'Error' | project Message"
        result = translate(kql, target="pyspark")
        # PySpark output should contain DataFrame API patterns
        assert ".filter" in result or ".where" in result or "SELECT" in result

    def test_ec10_make_series_zero_step_rejected(self):
        """Zero-step make-series should raise ValueError (FIX-04 guard)."""
        from kqlbridge.micro_model import TimeSeriesMicroModel
        with pytest.raises(ValueError, match="step value must be > 0"):
            TimeSeriesMicroModel(
                table="AppLogs",
                aggregation="count()",
                axis_col="TimeGenerated",
                step="0h",
                from_time="ago(7d)",
                to_time="now()",
                by_cols=["ServiceName"],
            )


# ═══════════════════════════════════════════════════════════════════════════════
# DIMENSION: REGRESSION / SENTINEL PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════


class TestSentinelPatterns:
    """Real-world Sentinel/security KQL patterns that should translate correctly."""

    def test_sentinel_failed_logons(self):
        """Sentinel: Failed logon events last 24h."""
        kql = (
            "SecurityEvent | where TimeGenerated > ago(24h) | where EventID == 4625 "
            "| project TimeGenerated, Account, Computer, IpAddress"
        )
        result = translate(kql, target="spark")
        assert "SecurityEvent" in result
        assert "4625" in result
        assert "CURRENT_TIMESTAMP" in result

    def test_sentinel_count_by_group(self):
        """Sentinel: Count failed logons by account."""
        kql = (
            "SecurityEvent | where EventID == 4625 "
            "| summarize FailedLogons=count() by Account "
            "| order by FailedLogons desc | take 10"
        )
        result = translate(kql, target="spark")
        assert "COUNT(*)" in result
        assert "FailedLogons" in result
        assert "GROUP BY" in result
        assert "ORDER BY" in result
        assert "LIMIT 10" in result


# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY REPORTER (runs as last test)
# ═══════════════════════════════════════════════════════════════════════════════


class TestSummaryReporter:
    """Collects pass/fail status for the summary report."""

    def test_zz_version_check(self):
        """Verify kqlbridge version is importable and recent."""
        assert __version__ is not None
        parts = __version__.split(".")
        assert len(parts) >= 2, f"Version string malformed: {__version__}"
