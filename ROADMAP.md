# KQLBridge Roadmap — Evolution to v0.8 & Subsequent PR Plan

This roadmap tracks the evolution of KQLBridge, marking the successful delivery of the **v0.7.0** milestone and outlining the scheduled capabilities for **v0.8.0** based on deep community telemetry and security operations (SOC) pain points.

---

## 🏆 Milestone v0.7.0 — Completed & Released (May 2026)
All major community-driven capabilities scheduled for v0.7 are now fully implemented, tested, and published to PyPI:
* [x] **`has_any()` Operator:** Word-boundary token matching utilizing RLIKE (`(?i)\b(...)`) on Spark and logical chain of `LIKE` matches on T-SQL.
* [x] **`percentile()` / `percentiles()` Aggregations:** High-performance approximate and continuous percentiles mapped to `approx_percentile` (Spark) and `PERCENTILE_CONT` (T-SQL).
* [x] **`make_list()` Aggregations:** dynamic list mapping using `collect_list` (Spark) and string fallback `STRING_AGG` (T-SQL).
* [x] **`serialize` State & `prev()` Window Function:** Mapped to SQL standard `LAG() OVER (ORDER BY (SELECT NULL))`.

---

## 📋 Scheduled Features — Milestone v0.8.0 (Community Pain Points)

Based on 5 deep community sweeps across platforms, the following 5 critical features are scheduled for the **v0.8.0** release:

### 1. Robust JSON Traversal (`parse_json(col).field`)
* **Use Case:** Processing nested semi-structured audit logs, system event fields, and JSON payloads (e.g., Sentinel/Log Analytics events).
* **Target SQL:**
  * **Spark SQL:** Translated to `from_json(col, schema).field` (or dynamic extraction using `get_json_object`).
  * **T-SQL:** Translated to standard JSON value retrieval `JSON_VALUE(col, '$.field')`.
* **Grammar/AST Requirements:**
  * Extend standard member access rules in `kql.lark` to handle indexing/property access on functions.
  * Map to a generic `JSONPathAccessExpr` AST node.

### 2. Array Unnesting & Explode (`mv-expand col`)
* **Use Case:** Expanding lists of nested records, groups, or multiple IP addresses into independent rows.
* **Target SQL:**
  * **Spark SQL:** Mapped to lateral views `LATERAL VIEW explode(col)`.
  * **T-SQL:** Mapped to cross applies using `CROSS APPLY OPENJSON(col)`.
* **Grammar/AST Requirements:**
  * Add `mv-expand` keyword and syntax as a pipeline operator in `kql.lark`.
  * Create `MvExpandOp` dataclass in `ast_nodes.py`.

### 3. Multi-Branch Evaluation (`case(c1, v1, c2, v2, ..., default)`)
* **Use Case:** Mapping severities, custom category descriptions, and conditional labels.
* **Target SQL:**
  * **Spark SQL & T-SQL:** Translated to SQL standard search `CASE WHEN c1 THEN v1 WHEN c2 THEN v2 ... ELSE default END`.
* **Grammar/AST Requirements:**
  * Add `case` expression to functional grammar matching alternating list of conditions and results.
  * Create `CaseExpr` AST node.

### 4. Threat Intelligence: Private IP Lookup (`ipv4_is_private(ip)`)
* **Use Case:** SOC threat analysis to separate public inbound traffic from private subnets.
* **Target SQL:**
  * **Spark & T-SQL:** Translated to checking standard private ranges `10.x.x.x`, `172.16.x.x` to `172.31.x.x`, `192.168.x.x`, and `127.x.x.x`.
* **Grammar/AST Requirements:**
  * Define `ipv4_is_private` signature under function calls in `kql.lark`.
  * Add corresponding evaluation rule inside translation generators.

### 5. Network Segmentation: Subnet Matching (`ipv4_is_in_range(ip, cidr)`)
* **Use Case:** Filtering logs to locate events originating from specified network security boundaries.
* **Target SQL:**
  * **Spark & T-SQL:** Mapped to bit-shifting prefix matches or custom range comparisons.
* **Grammar/AST Requirements:**
  * Parse CIDR notation parsing structures and create `IPv4InRangeExpr` AST nodes.

---

## 🛠 Implementation Cadence (v0.8)
1. **Parser & Grammar Extension:** Expand property matching rules in `kql.lark` to facilitate parse_json syntax.
2. **AST Consolidation:** Incorporate case logic and multi-branch arrays into the parser semantic pipeline.
3. **Dialect Customization:** Build target SQL generators and integrate Lateral View/OPENJSON operations.
4. **End-to-End Stress Testing:** Add 5 complex test cases covering arrays, JSON fields, and subnets.
