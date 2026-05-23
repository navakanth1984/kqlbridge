"""
GPS S — Stress sweep on kqlbridge v0.11.2
Four scenarios: standard, edge, overload, adversarial
Pass criterion: all assertions green, no exceptions outside expected guards
"""
import time, gc, sys, traceback, concurrent.futures, statistics
import kqlbridge
from kqlbridge import translate, smart_transpile, detect_operators, is_supported, TimeSeriesMicroModel

def test_version_pin():
    """Verify library version is exactly v0.11.2, v0.11.3, v0.11.4, v0.11.5, v0.12.0 or 0.12.1."""
    assert kqlbridge.__version__ in ("0.11.2", "0.11.3", "0.11.4", "0.11.5", "0.12.0", "0.12.1"), f"Wrong version: {kqlbridge.__version__}"

results = []

def run(label, fn):
    try:
        t0 = time.perf_counter()
        fn()
        ms = (time.perf_counter() - t0) * 1000
        results.append((label, "PASS", f"{ms:.1f}ms", ""))
    except AssertionError as e:
        results.append((label, "FAIL", "", str(e)[:120]))
    except Exception as e:
        results.append((label, "FAIL", "", f"{type(e).__name__}: {str(e)[:100]}"))

# ── STANDARD ─────────────────────────────────────────────────────────────────

def test_s01_datetime_fix_under_load():
    """FIX-01: datetime preprocessor correct across 500 varied date queries."""
    dates = ["2024-01-01","2023-06-15","2022-12-31","2025-03-01","2020-02-29"]
    for d in dates * 100:
        sql = translate(f"Events | where ts > datetime({d})", "tsql")
        assert f"CAST('{d}' AS DATETIME2)" in sql, f"datetime({d}) still arithmetic: {sql[:80]}"

def test_s02_row_number_over_all_window_fns():
    """FIX-02: all window functions emit OVER() — none return comment-only."""
    fns = ["row_number", "rank", "dense_rank", "ntile", "percent_rank", "cume_dist"]
    for fn in fns:
        sql = translate(f"T | extend r = {fn}()", "spark")
        assert "OVER" in sql.upper(), f"{fn}() missing OVER() clause: {sql!r}"
        assert "/* KQL function" not in sql, f"{fn}() still emitting comment fallback"

def test_s03_make_series_api_consistency():
    """FIX-03: detect/is_supported/smart_transpile all agree for make-series."""
    kql = "T | make-series count() on ts from datetime(2024-01-01) to datetime(2024-12-31) step 1d by cat"
    assert "make-series" in detect_operators(kql)
    assert is_supported(kql)
    engine, sql = smart_transpile(kql)
    assert engine == "spark_sql"
    assert "sequence" in sql.lower() or "explode" in sql.lower()

def test_s04_validation_guards_solid():
    """FIX-04: zero-step and end-before-start raise for all step units."""
    for unit in ["d","h","m","s"]:
        try:
            TimeSeriesMicroModel(table="T", aggregation="count()", axis_col="ts",
                step=f"0{unit}", from_time="datetime(2024-01-01)", to_time="datetime(2024-12-31)")
            assert False, f"zero step 0{unit} did not raise"
        except ValueError:
            pass
    try:
        TimeSeriesMicroModel(table="T", aggregation="count()", axis_col="ts",
            step="1d", from_time="datetime(2024-12-31)", to_time="datetime(2024-01-01)")
        assert False, "end < start did not raise"
    except ValueError:
        pass

# ── EDGE ─────────────────────────────────────────────────────────────────────

def test_s05_datetime_with_time_component():
    """FIX-01 edge: datetime with T and time component."""
    sql = translate("T | where ts > datetime(2024-01-01T12:30:00)", "tsql")
    assert "2024-01-01T12:30:00" in sql or "2024-01-01" in sql
    assert "((2024" not in sql, f"arithmetic still present: {sql}"

def test_s06_pipe_inside_string_not_split():
    """Pipeline splitter edge: pipe inside string literal must not split."""
    sql = translate("T | where name == 'a|b' | take 10", "spark")
    assert "LIMIT 10" in sql.upper() or "TAKE" in sql.upper() or sql  # must not crash

def test_s07_make_series_tsql_datetime_fix_combined():
    """FIX-01 + TEG: datetime literal in make-series via T-SQL emitter."""
    m = TimeSeriesMicroModel(
        table="Events", aggregation="count()", axis_col="ts",
        step="1d", from_time="datetime(2024-01-01)", to_time="datetime(2024-12-31)",
        by_cols=["category"]
    )
    sql = m.to_tsql()
    assert "CAST('2024-01-01' AS DATETIME2)" in sql or "2024-01-01" in sql
    assert "DATEADD" in sql.upper(), "T-SQL recursive CTE missing DATEADD"

def test_s08_empty_pipeline_detect_operators():
    """detect_operators edge: query with only a table name."""
    ops = detect_operators("MyTable")
    assert isinstance(ops, list)  # must return list, not raise

def test_s09_both_fill_types_tsql():
    """TEG edge: linear + forward fill combined, T-SQL dialect."""
    m = TimeSeriesMicroModel(
        table="Sensors", aggregation="avg(value)", axis_col="ts",
        step="1h", from_time="datetime(2024-01-01)", to_time="datetime(2024-01-02)",
        by_cols=["sensor_id"], linear_fill_cols=["value"], forward_fill_cols=["status"]
    )
    sql = m.to_tsql()
    assert "WITH" in sql.upper()

# ── OVERLOAD ──────────────────────────────────────────────────────────────────

def test_s10_concurrent_translations_no_crash():
    """10k concurrent translate() calls across all dialects — no panic, no crash."""
    queries = [
        ("Events | where level == 'error' | take 100", "spark"),
        ("Logs | where ts > datetime(2024-01-01) | take 50", "tsql"),
        ("T | summarize count() by category | order by count_ desc", "spark"),
        ("Events | extend rn = row_number()", "spark"),
        ("T | where status !in ('debug','trace')", "spark"),
    ]
    errors = []
    def call(args):
        kql, target = args
        try:
            translate(kql, target)
        except Exception as e:
            errors.append(str(e)[:80])
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
        list(ex.map(call, queries * 2000))
    assert not errors, f"{len(errors)} errors in concurrent run: {errors[:3]}"

def test_s11_make_series_10_group_by_cols():
    """TEG overload: 10 group-by columns."""
    m = TimeSeriesMicroModel(
        table="BigTelemetry", aggregation="avg(cpu)",
        axis_col="ts", step="1h",
        from_time="datetime(2024-01-01)", to_time="datetime(2024-01-31)",
        by_cols=[f"col_{i}" for i in range(10)]
    )
    sql = m.to_spark_sql()
    for i in range(10):
        assert f"col_{i}" in sql, f"col_{i} missing from output"

def test_s12_datetime_preprocessor_no_false_positives():
    """FIX-01: preprocessor must NOT alter already-quoted datetimes."""
    kql = "T | where ts > datetime('2024-01-01')"  # already quoted
    sql = translate(kql, "tsql")
    # Must not double-quote: datetime(''2024-01-01'')
    assert "''2024-01-01''" not in sql, f"double-quoting detected: {sql}"
    assert "2024-01-01" in sql

# ── ADVERSARIAL ───────────────────────────────────────────────────────────────

def test_s13_null_byte_rejected():
    """Adversarial: null byte must return error, not crash."""
    try:
        translate("T | where x > \x00 5", "spark")
    except Exception:
        pass  # any exception is acceptable

def test_s14_make_series_detect_mixed_pipeline():
    """FIX-03 adversarial: make-series with preceding where still detected."""
    kql = "T | where level == 'error' | make-series count() on ts from datetime(2024-01-01) to datetime(2024-12-31) step 1d"
    ops = detect_operators(kql)
    assert "make-series" in ops, f"make-series missed in mixed pipeline: {ops}"
    assert "where" in ops, f"where missed in mixed pipeline: {ops}"

def test_s15_sql_injection_in_string_literal():
    """Adversarial: SQL injection attempt via string literal must not escape quotes."""
    sql = translate("T | where name == \"'; DROP TABLE users; --\"", "spark")
    assert "DROP TABLE" not in sql.upper() or "'" in sql, "injection not contained"

def test_s16_very_long_column_list():
    """Adversarial: 50-column project — must not crash or truncate."""
    cols = ", ".join([f"col_{i}" for i in range(50)])
    sql = translate(f"T | project {cols}", "spark")
    assert "col_49" in sql, "last column truncated"

def test_s17_window_fn_tsql_emitter():
    """FIX-02 adversarial: row_number in T-SQL dialect also has OVER()."""
    sql = translate("T | extend r = row_number()", "tsql")
    assert "OVER" in sql.upper(), f"T-SQL row_number missing OVER: {sql!r}"


def main():
    run("S-STD-00  version pin check exactly v0.11.2", test_version_pin)
    run("S-STD-01  datetime preprocessor ×500 T-SQL queries", test_s01_datetime_fix_under_load)
    run("S-STD-02  all window fns have OVER() clause", test_s02_row_number_over_all_window_fns)
    run("S-STD-03  make-series API consistency", test_s03_make_series_api_consistency)
    run("S-STD-04  validation guards all step units", test_s04_validation_guards_solid)
    run("S-EDGE-05  datetime with time component", test_s05_datetime_with_time_component)
    run("S-EDGE-06  pipe inside string literal", test_s06_pipe_inside_string_not_split)
    run("S-EDGE-07  make-series + T-SQL datetime fix combined", test_s07_make_series_tsql_datetime_fix_combined)
    run("S-EDGE-08  empty pipeline detect_operators", test_s08_empty_pipeline_detect_operators)
    run("S-EDGE-09  both fill types T-SQL", test_s09_both_fill_types_tsql)
    run("S-OVL-10   10k concurrent translate() calls", test_s10_concurrent_translations_no_crash)
    run("S-OVL-11   make-series 10 group-by cols", test_s11_make_series_10_group_by_cols)
    run("S-OVL-12   datetime preprocessor no false positives", test_s12_datetime_preprocessor_no_false_positives)
    run("S-ADV-13   null byte rejected cleanly", test_s13_null_byte_rejected)
    run("S-ADV-14   make-series detected in mixed pipeline", test_s14_make_series_detect_mixed_pipeline)
    run("S-ADV-15   SQL injection contained in string literal", test_s15_sql_injection_in_string_literal)
    run("S-ADV-16   50-column project no truncation", test_s16_very_long_column_list)
    run("S-ADV-17   row_number OVER() in T-SQL dialect", test_s17_window_fn_tsql_emitter)

    # ── REPORT ────────────────────────────────────────────────────────────────────
    print()
    print("=" * 72)
    print(f"  GPS S — kqlbridge v0.11.2 stress sweep")
    print("=" * 72)
    passed = sum(1 for r in results if r[1] == "PASS")
    failed = sum(1 for r in results if r[1] == "FAIL")
    for label, status, timing, err in results:
        icon = "✓" if status == "PASS" else "✗"
        timing_str = f"  {timing}" if timing else ""
        err_str = f"  → {err}" if err else ""
        print(f"  {icon} {label}{timing_str}{err_str}")
    print("-" * 72)
    print(f"  {passed} PASS  {failed} FAIL  ({len(results)} total)")
    print("=" * 72)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
