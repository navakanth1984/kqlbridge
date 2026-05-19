# KQLBridge Market Research: Real-World Migration Pain Points

This document outlines the findings from community research (Reddit, StackOverflow, MS Fabric blogs) regarding the challenges of bridging KQL and SQL for large-scale data engineering.

## 1. The "SQL Brain" Join Trap
**Problem Statement:** Data engineers transitioning from SQL to KQL often attempt to join large tables and *then* filter, which is highly inefficient in distributed engines like Kusto or Spark.
**KQLBridge Solution:** KQLBridge correctly generates CTEs for `let` statements and preserves filters within those CTEs, ensuring that data is filtered *before* the join in the resulting SQL.
**Stress Test:** `Legacy Migration: Multi-Join Trap` in `market_stress_tests.py`.

## 2. Post-Aggregation Filtering (HAVING vs WHERE)
**Problem Statement:** KQL allows piping `where` after `summarize`. In SQL, this must be a `HAVING` clause or a subquery. Common transpilers often fail here by producing invalid `WHERE` clauses that reference aggregate aliases.
**KQLBridge Solution (Fixed):** I have updated the `SparkSQLGenerator` to detect post-summarize filters and wrap the query in a subquery, ensuring validity and semantic correctness.
**Stress Test:** `High-Cardinality Aggregations`.

## 3. T-SQL Compatibility & Semantic Drift
**Problem Statement:** T-SQL (Fabric SQL Warehouse) lacks many advanced string operators found in Kusto (like regex-based `has`).
**KQLBridge Solution (Fixed):** Updated `TSQLGenerator` to use `LIKE` as a safe fallback for `has`, preventing complete translation failure while acknowledging the semantic limitation.
**Stress Test:** `Pattern Match Stress (Has/Contains)`.

## 4. Time-Series Analysis at Scale
**Problem Statement:** Spark SQL's `DATE_TRUNC` is limited to standard intervals (hour, day). Custom intervals like `5m` or `15m` are common in KQL but complex in SQL.
**KQLBridge Solution:** KQLBridge implements custom bucketing logic using `UNIX_TIMESTAMP` and `FLOOR` to support arbitrary `bin()` intervals.
**Stress Test:** `Time-Series Binning Combinatorics`.

## 5. Query Complexity & Nesting
**Problem Statement:** Large enterprise queries often involve 10+ levels of nesting (iff statements, let chains).
**KQLBridge Solution:** Handled via recursive expression rendering and subquery wrapping for state changes.
**Stress Test:** `Deeply Nested Risk Scoring`.

## Known Limitations (Market Gaps)
- **Union at Start:** The current grammar requires a table name at the start of a query, preventing `union T1, T2` as the first line. This is a common pattern in ADX that needs a grammar update or preprocessor.
- **Lookup Operator:** The `lookup` operator (broadcast join) is currently missing from the AST and grammar. Community consensus is that `lookup` is critical for enriching large fact tables with small dimension tables without the overhead of a full `join`.

---
*Research conducted by Gemini CLI - May 2026*
