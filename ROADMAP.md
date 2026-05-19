# KQLBridge Roadmap — v0.7.1 Delivered → v0.8.0 Next

This roadmap tracks the evolution of KQLBridge from its current stable **v0.7.1** release through the **v0.8.0** community milestone.

---

## ✅ Milestone v0.7.0 — Completed & Released (May 2026)

Full SOC Threat Hunting feature set shipped:

* [x] `parse_json(col).field` → `get_json_object` (Spark) / `JSON_VALUE` (T-SQL)
* [x] `mv-expand col` → `LATERAL VIEW explode` (Spark) / `CROSS APPLY OPENJSON` (T-SQL)
* [x] `case(c1,v1,c2,v2,...,default)` → flat `CASE WHEN ... END` (both)
* [x] `ipv4_is_private(ip)` → RFC 1918 big-integer BETWEEN checks (both)
* [x] `ipv4_is_in_range(ip, cidr)` → dynamic CIDR-to-integer BETWEEN (both)
* [x] `has_any()` → RLIKE word-boundary (Spark) / LIKE chain (T-SQL)
* [x] `percentile()` / `percentiles()` → `approx_percentile` / `PERCENTILE_CONT`
* [x] `make_list()` → `collect_list` (Spark) / `STRING_AGG` (T-SQL)
* [x] `serialize` + `prev()` → `LAG() OVER (ORDER BY (SELECT NULL))`

---

## ✅ Milestone v0.7.1 — Patch Released (May 2026)

Critical correctness fix landed as a targeted patch:

* [x] **Boolean comparison fix:** Surgical `== true` stripping — only applied to `FuncCall`
  left-hand sides (which already emit native boolean SQL). `ColumnRef == true` comparisons
  now correctly render as `= TRUE` (satisfying the locked benchmark oracle).
* [x] **PySpark SOC test:** `test_soc_threat_hunting_pyspark` validates `parse_json`, `case`,
  and `ipv4_is_private` through `PySparkGenerator`, with `= true` suffix regression guard.
* [x] **Score:** 78/78 unit tests · 120/120 eval (100%)

---

## 🚀 Milestone v0.8.0 — Planned (Next Release)

Based on community telemetry, the following capabilities are prioritised for v0.8:

### 1. `format_datetime(col, format)` — Datetime Formatting
- **Pain Point:** Sentinel users constantly format timestamps for reports (`format_datetime(TimeGenerated, 'yyyy-MM-dd HH:mm')`).
- **Spark SQL:** `date_format(col, 'yyyy-MM-dd HH:mm')`
- **T-SQL:** `FORMAT(col, 'yyyy-MM-dd HH:mm')`

### 2. `tostring(col)` / `toint(col)` / `tolong(col)` / `todouble(col)` — Type Casting
- **Pain Point:** KQL type coercions ubiquitous in every schema normalisation pipeline.
- **Spark SQL:** `CAST(col AS STRING)` / `CAST(col AS INT)` / `CAST(col AS BIGINT)` / `CAST(col AS DOUBLE)`
- **T-SQL:** `CAST(col AS NVARCHAR(MAX))` / `CAST(col AS INT)` / `CAST(col AS BIGINT)` / `CAST(col AS FLOAT)`

### 3. `array_length(col)` / `array_index_of(arr, val)` — Array Inspection
- **Pain Point:** Common in threat hunting when counting matched IOCs or finding specific entries in arrays.
- **Spark SQL:** `size(col)` / `array_position(arr, val) - 1`
- **T-SQL:** `JSON_ARRAY_LENGTH(col)` / custom `OPENJSON` index lookup

### 4. `not in~` (case-insensitive NOT IN) — Case-Insensitive Exclusions
- **Pain Point:** SOC analysts frequently exclude known-good hostnames case-insensitively (`DeviceName !in~ ('desktop-abc', 'server-01')`).
- **Spark SQL:** `NOT (LOWER(col) IN (LOWER('val1'), LOWER('val2')))`
- **T-SQL:** `col NOT IN ('val1', 'val2')` (T-SQL is already case-insensitive by default collation)

### 5. Multi-Line `let` + Scalar Expression Chaining
- **Pain Point:** Analysts define multiple scalar `let` bindings that reference each other.
  ```kql
  let threshold = 100;
  let lookback = ago(7d);
  Events | where Count > threshold and TimeGenerated > lookback
  ```
- **Target:** Inline-substitute all scalar lets sequentially before final SQL emission.

### 6. `summarize ... by bin_auto(TimeGenerated)` — Auto-Bin Detection
- **Pain Point:** Power BI + Azure Monitor dashboards use `bin_auto` for adaptive time granularity.
- **Target:** Detect query time range and emit an appropriate `DATE_TRUNC` / `FLOOR` bin size.

---

## 🛠 Implementation Cadence (v0.8)

1. **Grammar First:** Extend `kql.lark` for `format_datetime`, type cast functions, `array_length`, `not in~`.
2. **AST Nodes:** Add `CastExpr`, `ArrayLenExpr`, `FormatDatetimeExpr` dataclasses (human decision — locked after merge).
3. **Generators:** Implement in `spark_sql.py` + override in `tsql.py` where dialect differs.
4. **Benchmark:** Add ≥10 cases to `tests/eval/benchmark.json` covering all new operators (must be locked before implementation).
5. **Stress Test:** Run community-driven real-world queries covering nested arrays + multi-let chains.

---

## 📦 Release Criteria (v0.8.0)

| Gate | Requirement |
|---|---|
| Unit tests | 90+ tests, 100% pass |
| Eval oracle | 130/130+ (new cases added) |
| Python support | 3.10, 3.11, 3.12, 3.13 |
| PyPI publish | `pip install kqlbridge==0.8.0` |
