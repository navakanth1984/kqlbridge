# KQLBridge Roadmap — v0.7 Release & Subsequent PR Plan

This roadmap tracks highly requested community features and enterprise patterns scheduled for implementation in the **v0.7** milestone.

---

## 📋 Scheduled Features

### 1. `has_any()` Operator
* **Use Case:** Ransomware file extension detection, threat hunting, and matching a string column against list of strings/extensions.
* **Target SQL:**
  * **Spark SQL:** Translated to a chain of `LIKE` or `RLIKE` matches to capture word boundaries or wildcards.
  * **T-SQL:** Translated to a sequence of `LIKE '%val1%' OR LIKE '%val2%'` operators.
* **Grammar/AST Requirements:**
  * Define `has_any` under `comparison` rules in `kql.lark`.
  * Create `HasAnyExpr` dataclass in `ast_nodes.py`.

### 2. `percentile()` Aggregation
* **Use Case:** SLA monitoring, performance latency reporting.
* **Target SQL:**
  * **Spark SQL:** Translated to `approx_percentile(Latency, pct / 100.0)`.
  * **T-SQL:** Translated to `PERCENTILE_CONT(pct / 100.0) WITHIN GROUP (ORDER BY Latency)`.
* **Grammar/AST Requirements:**
  * Add `percentile` function signature under `agg_func` in `kql.lark`.
  * Add `AggPercentile` dataclass in `ast_nodes.py`.

### 3. `make_list()` Aggregation
* **Use Case:** Grouping alerts, telemetry lines, or IP addresses into dynamic lists/arrays.
* **Target SQL:**
  * **Spark SQL:** Translated to `collect_list(col)`.
  * **T-SQL:** Translated to `STRING_AGG(col, ', ')`.
* **Grammar/AST Requirements:**
  * Add `make_list` function signature under `agg_func` in `kql.lark`.
  * Add `AggMakeList` dataclass in `ast_nodes.py`.

### 4. `serialize` and `prev()` Window Functions
* **Use Case:** Sessionization, time-gap analysis, and behavioral sequencing.
* **Target SQL:**
  * **Spark SQL & T-SQL:** If `prev(col)` is requested, translate it to analytic window function `LAG(col) OVER (ORDER BY [default_ordering_columns])`.
* **Grammar/AST Requirements:**
  * Add `serialize` pipeline operator to `pipe_op` and `serialize_op` in `kql.lark`.
  * Add `SerializeOp(PipeOp)` to `ast_nodes.py`.

---

## 🛠 Implementation Cadence (v0.7)
1. **Unlock Phase:** Temporarily lift standard human-only lock constraints on `kql.lark` and `ast_nodes.py`.
2. **Grammar & Parser Integration:** Implement exact parser logic to build target AST structures.
3. **Generator Mapping:** Add dialect-specific translations to `SparkSQLGenerator` and `TSQLGenerator`.
4. **Validation:** Extend `tests/test_operators.py` with the 12 complex real-world threat hunting queries under these features.
