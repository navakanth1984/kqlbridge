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

## ✅ Milestone v0.8.0 — Completed & Released (May 2026)

Full array manipulation, casting, formatting, and case-insensitive comparison support:

* [x] **`format_datetime(col, format)`**: Fully implemented for Spark SQL (`DATE_FORMAT`) and T-SQL (`FORMAT`).
* [x] **Explicit Casting**: Standardized translation for `tostring`, `toint`, `tolong`, and `todouble` across dialects.
* [x] **Array Operations**: Robust indexing support via `array_length` and `array_index_of` with correct KQL 0-based indexing mappings.
* [x] **Case-Insensitive List membership (`in~`, `!in~`)**: Grammar and generator capabilities fully integrated for both literal sets and subqueries.
* [x] **Score:** 81/81 unit tests (100% success) · Published to PyPI and Test PyPI.

---

## 🚀 Milestone v0.9.0 — Planned (Next Release)

Based on community roadmap priorities, the following items are scheduled for the next development iteration:

### 1. Multi-Line `let` + Scalar Expression Chaining
- **Pain Point:** Analysts define multiple scalar `let` bindings that reference each other.
  ```kql
  let threshold = 100;
  let lookback = ago(7d);
  Events | where Count > threshold and TimeGenerated > lookback
  ```
- **Target:** Inline-substitute all scalar lets sequentially before final SQL emission.

### 2. `summarize ... by bin_auto(TimeGenerated)` — Auto-Bin Detection
- **Pain Point:** Power BI + Azure Monitor dashboards use `bin_auto` for adaptive time granularity.
- **Target:** Detect query time range and emit an appropriate `DATE_TRUNC` / `FLOOR` bin size.

---

## 🛠 Implementation Cadence (v0.9)

1. **Let substitution compiler pass**: Build inline parser pass in `src/kqlbridge/parser.py`.
2. **Auto-bin interval resolver**: Implement fallback resolution based on active query context.
3. **Benchmark additions**: Add nested let binding edge-cases to `tests/eval/benchmark.json`.

---

## 📦 Release Criteria (v0.9.0)

| Gate | Requirement |
|---|---|
| Unit tests | 95+ tests, 100% pass |
| Eval oracle | 140/140+ (new cases added) |
| Python support | 3.10, 3.11, 3.12, 3.13 |
| PyPI publish | `pip install kqlbridge==0.9.0` |

