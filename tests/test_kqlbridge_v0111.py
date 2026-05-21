"""
kqlbridge v0.11.0 — GPS-governed pytest suite
QA Engineer + Developer/Architect dual-role
Live tests against PyPI kqlbridge==0.11.0
"""
import pytest
import re
import kqlbridge
from kqlbridge import (
    translate, smart_transpile, detect_operators,
    is_supported, check, TimeSeriesMicroModel
)

# ═══════════════════════════════════════════════════════
# GPS PREFLIGHT — version pin guard
# ═══════════════════════════════════════════════════════

def test_version_pin():
    """GPS P: eval oracle must run against a known version. Never skip."""
    assert kqlbridge.__version__ == "0.11.1", (
        f"Wrong version: {kqlbridge.__version__!r}. "
        "These tests are calibrated for v0.11.0 only."
    )

# ═══════════════════════════════════════════════════════
# CATEGORY: Baseline — existing Tier 1 operators
# Must not regress from v0.10.0
# ═══════════════════════════════════════════════════════

class TestBaseline:
    def test_where_spark(self):
        sql = translate("Events | where level == 'error'", "spark")
        assert "WHERE" in sql.upper()
        assert "level" in sql
        assert "error" in sql

    def test_project_spark(self):
        sql = translate("Events | where level == 'error' | project timestamp, message", "spark")
        assert "timestamp" in sql
        assert "message" in sql
        assert "SELECT" in sql.upper()

    def test_where_tsql_non_datetime(self):
        sql = translate("Logs | where level == 'warn'", "tsql")
        assert "WHERE" in sql.upper()
        assert "warn" in sql

    def test_union_spark(self):
        sql = translate("Events | union OtherEvents", "spark")
        assert "UNION" in sql.upper()

    def test_uppercase_keywords(self):
        """PR #3: keyword normalisation — uppercase KQL must be handled."""
        sql = translate("Events | WHERE level == 'error' | PROJECT timestamp, message", "spark")
        assert "timestamp" in sql
        assert "message" in sql

# ═══════════════════════════════════════════════════════
# CATEGORY: P0 BUG — T-SQL datetime arithmetic (PR #1)
# GPS P: this blocks stable release
# ═══════════════════════════════════════════════════════

class TestPR1_TsqlDatetime:
    """All tests in this class confirm the P0 bug from PR #1."""

    def test_datetime_tsql_emits_arithmetic_NOT_cast(self):
        """
        GPS S adversarial: confirmed bug.
        datetime(2024-01-01) in T-SQL emits CONVERT(datetime, ((2024-1)-1))
        which is arithmetic on year/month/day integers — wrong.
        This test FAILS until PR #1 is merged.
        """
        sql = translate("Events | where timestamp > datetime(2024-01-01)", "tsql")
        # Bug: actual output contains arithmetic expression
        assert "((2024 - 1) - 1)" not in sql, (
            "PR#1 BUG CONFIRMED: datetime(2024-01-01) emitted as arithmetic. "
            f"Actual SQL: {sql!r}"
        )
        # Correct: should emit a cast of the ISO string
        assert re.search(r"CAST\('2024-01-01' AS DATETIME2\)", sql), (
            f"Expected CAST('2024-01-01' AS DATETIME2) in T-SQL output. Got: {sql!r}"
        )

    def test_datetime_tsql_year_boundary(self):
        sql = translate("T | where ts > datetime(2023-12-31)", "tsql")
        assert "((2023 - 12) - 31)" not in sql
        assert "2023-12-31" in sql

    def test_datetime_tsql_range(self):
        sql = translate("T | where ts between (datetime(2024-01-01) .. datetime(2024-12-31))", "tsql")
        assert "2024-01-01" in sql
        assert "2024-12-31" in sql

# ═══════════════════════════════════════════════════════
# CATEGORY: P0 BUG — ExtendOp row_number no OVER() (PR #5)
# GPS S: invalid SQL at execution time
# ═══════════════════════════════════════════════════════

class TestPR5_ExtendOp:
    def test_row_number_must_have_over_clause(self):
        """
        row_number() without OVER() is invalid SQL in every engine.
        This test FAILS until PR #5 is merged.
        """
        sql = translate("Events | extend rn = row_number()", "spark")
        assert "OVER" in sql.upper(), (
            f"row_number() emitted without OVER() clause. Invalid SQL. Got: {sql!r}"
        )
        # Should NOT emit the comment-only fallback
        assert "/* KQL function" not in sql, (
            f"row_number() emitted comment placeholder instead of proper window spec. Got: {sql!r}"
        )

    def test_rank_must_have_over_clause(self):
        sql = translate("Events | extend r = rank()", "spark")
        assert "OVER" in sql.upper()

# ═══════════════════════════════════════════════════════
# CATEGORY: P0 BUG — API trust gap: make-series detection
# detect_operators / is_supported lie about TEG v5 support
# ═══════════════════════════════════════════════════════

class TestAPITrustGap:
    MAKE_SERIES_KQL = "T | make-series count() on ts from datetime(2024-01-01) to datetime(2024-12-31) step 1d by category"

    def test_detect_operators_finds_make_series(self):
        """
        GPS G finding: detect_operators returns [] for make-series.
        This test FAILS until the operator registry is updated.
        """
        ops = detect_operators(self.MAKE_SERIES_KQL)
        assert "make-series" in ops, (
            f"detect_operators missed 'make-series' — API out of sync with TEG v5. Got: {ops!r}"
        )

    def test_is_supported_make_series(self):
        """is_supported returns False despite translate() working. FAILS until fixed."""
        assert is_supported(self.MAKE_SERIES_KQL), (
            "is_supported('make-series...') returned False despite TEG v5 supporting it."
        )

    def test_smart_transpile_make_series(self):
        """smart_transpile raises parser error on make-series. FAILS until fixed."""
        engine, sql = smart_transpile(self.MAKE_SERIES_KQL)
        assert engine in ("spark_sql", "pyspark", "tsql")
        assert "grid" in sql.lower() or "sequence" in sql.lower() or "explode" in sql.lower()

    def test_check_returns_valid_for_make_series(self):
        result = check(self.MAKE_SERIES_KQL)
        assert result.is_valid, f"check() returned invalid for supported make-series query: {result!r}"

# ═══════════════════════════════════════════════════════
# CATEGORY: TEG v5 — TimeSeriesMicroModel correctness
# These PASS in v0.11.0
# ═══════════════════════════════════════════════════════

class TestTEGv5Core:
    def _model(self, **kwargs):
        defaults = dict(
            table="Events", aggregation="count()", axis_col="timestamp",
            step="1d", from_time="datetime(2024-01-01)", to_time="datetime(2024-12-31)",
            by_cols=["category"]
        )
        defaults.update(kwargs)
        return TimeSeriesMicroModel(**defaults)

    def test_spark_sql_grid_generation(self):
        sql = self._model().to_spark_sql()
        assert "sequence(" in sql.lower()
        assert "explode(" in sql.lower()
        assert "WITH" in sql.upper()
        assert "grid" in sql.lower()

    def test_tsql_recursive_cte(self):
        sql = self._model().to_tsql()
        assert "WITH" in sql.upper()
        assert "DATEADD" in sql.upper()
        assert "UNION ALL" in sql.upper()

    def test_pandas_output(self):
        code = self._model().to_pandas()
        assert "import pandas" in code
        assert "date_range" in code or "pd.to_datetime" in code

    def test_pyspark_output(self):
        code = self._model().to_pyspark()
        assert "from pyspark" in code or "F.col" in code

    def test_series_fill_linear(self):
        sql = self._model(linear_fill_cols=["value"]).to_spark_sql()
        assert sql  # must produce output
        assert "WITH" in sql.upper()

    def test_series_fill_forward(self):
        sql = self._model(forward_fill_cols=["status"]).to_spark_sql()
        assert sql
        assert "WITH" in sql.upper()

    def test_linear_and_forward_combined(self):
        sql = self._model(
            linear_fill_cols=["reading"],
            forward_fill_cols=["status"]
        ).to_spark_sql()
        assert sql

    def test_five_group_by_columns(self):
        """GPS S overload: 5 group-by columns."""
        sql = self._model(by_cols=["region","dc","rack","server","core"]).to_spark_sql()
        for col in ["region","dc","rack","server","core"]:
            assert col in sql

    def test_no_by_cols_ungrouped(self):
        """GPS S edge: ungrouped make-series (no by_cols)."""
        m = TimeSeriesMicroModel(
            table="T", aggregation="count()", axis_col="ts",
            step="1d", from_time="datetime(2024-01-01)", to_time="datetime(2024-01-31)"
        )
        sql = m.to_spark_sql()
        assert "sequence(" in sql.lower()

    def test_hourly_step(self):
        m = TimeSeriesMicroModel(
            table="Sensors", aggregation="avg(value)", axis_col="ts",
            step="1h", from_time="datetime(2024-01-01)", to_time="datetime(2024-01-02)"
        )
        sql = m.to_spark_sql()
        assert "HOUR" in sql.upper() or "hour" in sql.lower()

    def test_kql_string_init(self):
        m = TimeSeriesMicroModel(
            "T | make-series count() on ts from datetime(2024-01-01) to datetime(2024-12-31) step 1d by category"
        )
        sql = m.to_spark_sql()
        assert "sequence(" in sql.lower()

# ═══════════════════════════════════════════════════════
# CATEGORY: Edge case validation guards (FIX-04)
# These FAIL until FIX-04 is applied — silent runtime bombs
# ═══════════════════════════════════════════════════════

class TestEdgeCaseGuards:
    def test_zero_step_must_raise(self):
        """GPS S: step=0d generates infinite sequence in Spark — must raise."""
        with pytest.raises((ValueError, Exception)):
            m = TimeSeriesMicroModel(
                table="T", aggregation="count()", axis_col="ts",
                step="0d",
                from_time="datetime(2024-01-01)", to_time="datetime(2024-12-31)"
            )
            m.to_spark_sql()  # raise may occur here or in __init__

    def test_end_before_start_must_raise(self):
        """GPS S: end < start emits SQL silently — must raise."""
        with pytest.raises((ValueError, Exception)):
            m = TimeSeriesMicroModel(
                table="T", aggregation="count()", axis_col="ts",
                step="1d",
                from_time="datetime(2024-12-31)",
                to_time="datetime(2024-01-01)"
            )
            m.to_spark_sql()

    def test_empty_table_name_must_raise(self):
        with pytest.raises((ValueError, TypeError, Exception)):
            m = TimeSeriesMicroModel(
                table="", aggregation="count()", axis_col="ts",
                step="1d",
                from_time="datetime(2024-01-01)", to_time="datetime(2024-12-31)"
            )
            m.to_spark_sql()

# ═══════════════════════════════════════════════════════
# CATEGORY: Open PRs — confirm or refute each issue
# ═══════════════════════════════════════════════════════

class TestOpenPRs:
    def test_pr1_tsql_datetime_is_broken(self):
        """Document the confirmed PR #1 bug for CI tracking."""
        sql = translate("Events | where timestamp > datetime(2024-01-01)", "tsql")
        # Mark as xfail until PR #1 is merged
        if "((2024 - 1) - 1)" in sql:
            pytest.xfail("PR #1 not yet merged: T-SQL datetime arithmetic bug active")

    def test_pr3_uppercase_kql_passes(self):
        """PR #3: keyword normalisation — CONFIRMED PASSING in v0.11.0."""
        sql = translate("Events | WHERE level == 'error'", "spark")
        assert "WHERE" in sql.upper() or "where" in sql.lower()

    def test_pr5_row_number_bug(self):
        """Document confirmed PR #5 bug."""
        sql = translate("Events | extend rn = row_number()", "spark")
        if "/* KQL function" in sql and "OVER" not in sql.upper():
            pytest.xfail("PR #5 not yet merged: row_number() without OVER() clause")

    def test_pr7_complex_query_perf(self):
        """PR #7: complex test performance — ensure no timeout."""
        import time
        kql = " | ".join([
            "BigTable",
            "where category in ('A','B','C','D','E')",
            "where timestamp > datetime(2024-01-01)",
            "summarize count(), avg(value) by category, region",
            "order by count_ desc",
            "take 1000"
        ])
        start = time.time()
        try:
            translate(kql, "spark")
        except Exception:
            pass
        elapsed = time.time() - start
        assert elapsed < 5.0, f"translate() took {elapsed:.2f}s on complex query — PR #7 perf concern"

    def test_pr8_not_in_passes(self):
        """PR #8: !in keyword — CONFIRMED PASSING in v0.11.0."""
        sql = translate("Events | where level !in ('debug', 'trace')", "spark")
        assert "NOT IN" in sql.upper()
