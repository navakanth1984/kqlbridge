# Graph Report - kqlbridge  (2026-05-21)

## Corpus Check
- 42 files · ~43,906 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 889 nodes · 1529 edges · 47 communities (45 shown, 2 thin omitted)
- Extraction: 83% EXTRACTED · 17% INFERRED · 0% AMBIGUOUS · INFERRED: 254 edges (avg confidence: 0.62)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c60ddc86`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]

## God Nodes (most connected - your core abstractions)
1. `SparkSQLGenerator` - 75 edges
2. `translate()` - 74 edges
3. `sql()` - 61 edges
4. `PySparkGenerator` - 49 edges
5. `TSQLGenerator` - 30 edges
6. `TimeSeriesMicroModel` - 26 edges
7. `ExplainResult` - 25 edges
8. `_build_expr()` - 22 edges
9. `LintIssue` - 20 edges
10. `parse()` - 20 edges

## Surprising Connections (you probably didn't know these)
- `run()` --calls--> `parse()`  [INFERRED]
  run_stress_test.py → src/kqlbridge/parser.py
- `run()` --calls--> `smart_transpile()`  [INFERRED]
  run_stress_test.py → src/kqlbridge/smart.py
- `route_query()` --calls--> `translate()`  [INFERRED]
  examples/fabric_migration/01_simple_filter.py → src/kqlbridge/__init__.py
- `run_advanced_stress_tests()` --calls--> `translate()`  [INFERRED]
  examples/market_pain_points/advanced_stress_tests.py → src/kqlbridge/__init__.py
- `run_market_stress_tests()` --calls--> `translate()`  [INFERRED]
  examples/market_pain_points/market_stress_tests.py → src/kqlbridge/__init__.py

## Communities (47 total, 2 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (101): PySparkGenerator, Main entry point for PySpark generation., Experimental PySpark Generator.     Routes KQL AST nodes to executable PySpark D, Generates Spark SQL from a KQLQuery AST.      Usage:         gen = SparkSQLGener, SparkSQLGenerator, Generates T-SQL from a KQLQuery AST.     Inherits from SparkSQLGenerator — overr, TSQLGenerator, AggAvg (+93 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (17): lines(), test_operators.py — Per-Operator Unit Tests ====================================, Shorthand: translate KQL → Spark SQL., Split result into non-empty lines for structural checks., sql(), TestAgo, TestBin, TestCount (+9 more)

### Community 2 - "Community 2"
Cohesion: 0.04
Nodes (44): 1. Flounder IR, 2. Apache Arrow DataFusion LogicalPlan / PhysicalPlan, 3. Substrait: Universal Query Plan Format, 4. MLIR for Database Query Compilation, 5. Ibis Project: Multi-Backend DataFrame Abstraction, 6. SQLGlot: Multi-Dialect SQL Transpiler, Architecture, Architecture (+36 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (42): 1. Semantic Parsing Architectures for SQL (2024-2025), 2. Grammar-Constrained Decoding (PICARD, XGrammar), 3. NL2KQL Architecture (Schema Refiner + Few-Shot Selector + Query Refiner), 4. Small Language Models (SLMs) for Code Translation, 5. Tree-to-Tree Neural Translation, 6. Execution-Guided Synthesis, 7. WASM-Based Micro Language Runtime, Alternative: Compile the Grammar/IR to Rust/Go (+34 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (28): generators/spark_sql.py — KQL AST → Spark SQL ==================================, # NOTE: do NOT clear where_clauses — WHERE filters from before, # NOTE: do NOT clear where_clauses — WHERE filters from before, generators/tsql.py — KQL AST → T-SQL ===================================== AGENT, check(), is_supported(), kqlbridge — KQL to Spark SQL / T-SQL transpiler ================================, Return True if the query can be fully translated to Spark SQL.      Queries with (+20 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (19): Walk the pipe operators and accumulate SQL clause fragments.         The assembl, Returns (select_cols, group_by_cols).          Karpathy P5 — Jagged Intelligence, Render a single aggregation expression., Returns (select_cols, group_by_cols).          Karpathy P5 — Jagged Intelligence, KQL join → SQL INNER/LEFT/RIGHT/FULL JOIN.         Returns a 'table expression', Render a single aggregation expression., KQL union T1, T2 or union (T1 | ...) → UNION ALL, Render bin(col, N<unit>) → Spark SQL timestamp bucketing.         - Hourly or co (+11 more)

### Community 6 - "Community 6"
Cohesion: 0.13
Nodes (34): ExtendOp, | extend alias = expr, _build_agg_item(), _build_agg_list(), _build_distinct(), _build_extend(), _build_groupby_list(), _build_iff_chain() (+26 more)

### Community 7 - "Community 7"
Cohesion: 0.13
Nodes (13): format_step(), format_time_expr(), get_default_alias(), parse_step(), parse_time_expr(), KQL Time Series Window and Interpolation Compiler.          Translates 'make-ser, TimeSeriesMicroModel is a KQL time-series compiler that translates     make-seri, TimeSeriesMicroModel (+5 more)

### Community 8 - "Community 8"
Cohesion: 0.12
Nodes (23): _check(), _explain(), _lint(), main(), _operators(), cli.py — KQLBridge command-line interface ======================================, _translate(), _version() (+15 more)

### Community 9 - "Community 9"
Cohesion: 0.06
Nodes (30): 01 · `where` → `WHERE clause`, 02 · `project` → `SELECT columns`, 03 + 04 · `summarize` → `GROUP BY + aggregations`, 05 · `bin()` → `DATE_TRUNC / FLOOR`, 06 · `ago()` → `CURRENT_TIMESTAMP - INTERVAL`, 07 · `extend` → `SELECT *, computed_col AS expr`, 08 · `order by` / `sort by` → `ORDER BY`, 09 · `take` / `limit` → `LIMIT n` (+22 more)

### Community 10 - "Community 10"
Cohesion: 0.16
Nodes (21): is_clean(), lint(), LintIssue, lint.py — KQLBridge Semantic Drift Detector ====================================, LINT-03: bin(ts, 7d) buckets from Unix epoch, not calendar weeks., LINT-04: let bindings that reference earlier bindings may not resolve., LINT-05: extend col = col — self-assignment is ambiguous in Spark SQL., LINT-06: distinct * after project returns same rows as project alone. (+13 more)

### Community 11 - "Community 11"
Cohesion: 0.08
Nodes (17): examples/fabric_migration/01_simple_filter.py ==================================, The routing agent pattern from DE-Context Kit.     Routes each query to the most, route_query(), detect_operators(), Return the list of KQL operators used in a query string.      Useful for routing, Return the list of KQL operators used in a query string.      Useful for routing, Return the list of KQL operators used in a query string.      Useful for routing, Return the list of KQL operators used in a query string.      Useful for routing (+9 more)

### Community 12 - "Community 12"
Cohesion: 0.13
Nodes (7): Translate a KQL query string to the target SQL dialect.      Args:         kql:, Translate a KQL query string to the target SQL dialect.      Args:         kql:, Translate a KQL query string to the target SQL dialect.      Args:         kql:, translate(), TestCommunityFunctions, TestV07Features, TestV08Features

### Community 13 - "Community 13"
Cohesion: 0.09
Nodes (21): 1. Jules Diagnostic Logging System (`.jules/`), 2. Interactive CLI Debugging, 3. Parsing and Lark AST Inspection, 4. IDE Debugging Setup (VS Code), 5. Adversarial Score Verification (`prepare.py`), 6. Real-time Debugging Logs, code:markdown (# FAILURE: Complex Filtering and Extend), code:block2 (+13 more)

### Community 14 - "Community 14"
Cohesion: 0.1
Nodes (20): Architecture, CLI, code:python (from kqlbridge import translate), code:bash (pip install kqlbridge), code:python (from kqlbridge import translate, detect_operators, is_suppor), code:bash (# Translate to Spark SQL (default)), code:bash (python tests/eval/prepare.py), code:block6 (KQL input) (+12 more)

### Community 15 - "Community 15"
Cohesion: 0.1
Nodes (19): 1. GPS Framework — Full Sweep, 2.1 Test Results After Fix Pass, 2.2 Fix Summary, 2. Code Fixes — All Failing Tests, 3. Stress Test Status, 4. CDLC Layer Coverage, 5. Karpathy Bloat Audit — Post AutoResearch Run, 6. AutoResearch Loop — Configuration (+11 more)

### Community 16 - "Community 16"
Cohesion: 0.12
Nodes (9): Test edge cases and boundary conditions., Test extend with minimal operations., Test project with single column., Test count operator without other operations., Test distinct on specific columns., Test order by with multiple columns and directions., Test null value comparisons., Test !in operator (not in). (+1 more)

### Community 17 - "Community 17"
Cohesion: 0.12
Nodes (9): Test complex real-world KQL queries., Test multiple nested iff() function calls., Test summarize with multiple conditional aggregations., Test union of tables with different column sets., Test complex WHERE clause with AND/OR nesting., Test bin() with various time intervals., Test extend with many computed column expressions., Test various string operations. (+1 more)

### Community 18 - "Community 18"
Cohesion: 0.12
Nodes (15): AutoResearch Mapping, BIT Loop Cadence, Bloat Audit Checklist (run after every successful Build), code:block1 (prepare.py → SCORE: {pct:.1f}% ({pass}/{total})), code:block2 (src/kqlbridge/parser.py), code:block3 (tests/eval/prepare.py       # 🔒 LOCKED oracle — the eval scr), code:block4 (tests/eval/prepare.py returns SCORE ≥ 85.0%), code:block5 (□ Can any 10+ line block become a named function?) (+7 more)

### Community 19 - "Community 19"
Cohesion: 0.14
Nodes (8): Regression tests for known issues., Regression: !in operator should be properly parsed., Regression: extend followed by summarize should work., Regression: union followed by additional operations., Test real-world Sentinel: failed login spikes per hour., Test real-world Sentinel: suspicious powershell processes joined with network ev, Test real-world Sentinel: multi-location login alerts., TestRegression

### Community 20 - "Community 20"
Cohesion: 0.14
Nodes (13): 1. GPS as the governing ring, 2. GPS run on this architecture, 3. Architectural decisions, 4. Complete test ledger — after architecture pass, 5. Next sprint — GPS-gated delivery plan, ADR-01: Pipeline AST — []Node chain replaces single *Node, ADR-02: Capability Tier system (Tier 1 / 2 / 3), ADR-03: Flattening translator + CTE chain for Tier 2 (+5 more)

### Community 21 - "Community 21"
Cohesion: 0.15
Nodes (12): `bag_unpack()`, code:kql (// No SQL equivalent — keep in KQL engine), code:python (from kqlbridge import is_supported, check), Deferred to v0.2, How to Handle Unsupported Operators, `ipv4_is_in_range()` / `ipv4_compare()`, `make-series`, Permanently Out of Scope (+4 more)

### Community 22 - "Community 22"
Cohesion: 0.17
Nodes (6): test_stress.py — KQLBridge Stress & Regression Tests ===========================, Test join operations (if implemented)., Test basic inner join., Stress tests representing highly complex, real-world security analytics & threat, TestAdvancedThreatHuntingQueries, TestJoinOperations

### Community 23 - "Community 23"
Cohesion: 0.24
Nodes (10): _canonical_match(), _canonicalize(), _is_syntactically_valid(), main(), prepare.py — KQLBridge Eval Oracle =================================== LOCKED FI, Check structural equivalence via canonical form., Check that the generated SQL is parseable by sqlglot as Spark SQL., Score a single benchmark case.      Returns (score: int, failure_reason: Optiona (+2 more)

### Community 24 - "Community 24"
Cohesion: 0.17
Nodes (11): Bug Reports, Code Style, code:block1 (tests/eval/prepare.py       # Eval oracle — LOCKED), code:bash (# 1. Fork and clone), code:block3 (**KQL input:** `AppLogs | where ...`), Contributing to KQLBridge, How to Contribute, License (+3 more)

### Community 25 - "Community 25"
Cohesion: 0.18
Nodes (10): 1. Multi-Line `let` + Scalar Expression Chaining, 2. `summarize ... by bin_auto(TimeGenerated)` — Auto-Bin Detection, code:kql (let threshold = 100;), 🛠 Implementation Cadence (v0.9), KQLBridge Roadmap — v0.7.1 Delivered → v0.8.0 Next, ✅ Milestone v0.7.0 — Completed & Released (May 2026), ✅ Milestone v0.7.1 — Patch Released (May 2026), ✅ Milestone v0.8.0 — Completed & Released (May 2026) (+2 more)

### Community 26 - "Community 26"
Cohesion: 0.29
Nodes (9): _check_architecture_rules(), scripts/graphify_audit.py — KQLBridge Codebase Intelligence via Graphify =======, Fallback analysis without graphify — uses Python's ast module., Karpathy Principle 6 bloat audit checklist — run after every Tune phase., Check architectural invariants for the KQLBridge codebase.     These rules shoul, Full 7-step graphify pipeline on the KQLBridge source., _run_bloat_audit(), run_graphify_pipeline() (+1 more)

### Community 27 - "Community 27"
Cohesion: 0.2
Nodes (6): Test type conversion functions., Test tostring() function., Test toint() function., Test todouble() function., Test multiple type conversions in sequence., TestTypeConversions

### Community 28 - "Community 28"
Cohesion: 0.2
Nodes (6): Test datetime-related operations., Test datetime() literal syntax., Test datetime_diff() function., Test datetime_add() function., Test ago() time expression., TestDateTimeOperations

### Community 29 - "Community 29"
Cohesion: 0.22
Nodes (9): 3. DuckDB Time-Series Features, code:sql (-- DuckDB native time bucketing), code:sql (SELECT t.*, p.price), code:sql (SELECT *), code:sql (-- DuckDB gap-fill via generate_series + lateral join), Gap-Fill via generate_series, KQL Micro Model Opportunity, Native ASOF JOIN (DuckDB's killer feature) (+1 more)

### Community 30 - "Community 30"
Cohesion: 0.25
Nodes (5): Test that queries don't have pathological performance issues., Test summarize with many aggregation functions., Test deeply nested where clauses., Test projection with many columns., TestPerformanceCharacteristics

### Community 31 - "Community 31"
Cohesion: 0.25
Nodes (7): 1. The "SQL Brain" Join Trap, 2. Post-Aggregation Filtering (HAVING vs WHERE), 3. T-SQL Compatibility & Semantic Drift, 4. Time-Series Analysis at Scale, 5. Query Complexity & Nesting, Known Limitations (Market Gaps), KQLBridge Market Research: Real-World Migration Pain Points

### Community 32 - "Community 32"
Cohesion: 0.25
Nodes (8): 2. TimescaleDB: time_bucket_gapfill(), Architecture, Architecture Notes, code:sql (SELECT), code:sql (-- TimescaleDB:  interpolate(avg(temperature))), Key Insight for KQL Micro Model, Syntax, Translation to Standard SQL

### Community 33 - "Community 33"
Cohesion: 0.25
Nodes (8): 6. Flink SQL: Streaming Time Windows, code:sql (-- Tumbling window (non-overlapping fixed size)), code:sql (-- Enrich orders with price at the time of the order), code:sql (-- Generate time spine as a source), Gap-Filling in Flink SQL, KQL Translation Insight, Temporal Join (Event time + Versioned table), Window TVF Syntax (Flink 1.13+)

### Community 34 - "Community 34"
Cohesion: 0.25
Nodes (8): 1. TSQL2 / SQL:2011 Temporal Tables (ISO Standard), Allen's Interval Operators in SQL:2011, code:sql (-- Overlap: A overlaps B), code:sql (-- Step 1: Mark interval starts (where previous row's end !=), KQL Translation, Snodgrass Coalescing (PACK / COALESCE), SQL Island-Grouping Pattern for COALESCE:, The Standard

### Community 36 - "Community 36"
Cohesion: 0.29
Nodes (6): 2026-05-16 — Session 0: Repo scaffold, Bloat Audit History, Current Eval Score, Operator Coverage, Operator Status — KQLBridge v0.1, Session Log

### Community 37 - "Community 37"
Cohesion: 0.29
Nodes (7): 4. InfluxDB Flux Language, code:kql (// KQL equivalent), code:flux (// Flux: time-series aggregation with gap fill), Key Design Insight, KQL Parallel, Pipe-Forward Operator Model, Semantic Differences: Flux vs KQL

### Community 38 - "Community 38"
Cohesion: 0.29
Nodes (7): 5. PromQL / MetricsQL, code:promql (# Instant vector: value at a single moment), code:promql (# Linear interpolation (MetricsQL extension)), Key Semantic Differences from SQL, KQL Translation Opportunity, MetricsQL Extensions (VictoriaMetrics), Range Vectors & Instant Vectors

### Community 39 - "Community 39"
Cohesion: 0.33
Nodes (4): Test IPv4-specific functions., Test ipv4_is_private() function., Test ipv4_is_in_range() function., TestIPv4Operations

### Community 40 - "Community 40"
Cohesion: 0.33
Nodes (6): 7. Snodgrass Temporal DB: COALESCE, PACK, UNPACK Operators, COALESCE, code:sql (-- Snodgrass SQL/Temporal COALESCE rewrite pattern), Connection to KQL, PACK (Temporal Projection), UNPACK (Discretization)

### Community 41 - "Community 41"
Cohesion: 0.5
Nodes (3): Executive Summary, Research: Time-Series Languages & Databases for KQL Micro Model, Summary: Translation Matrix

## Knowledge Gaps
- **344 isolated node(s):** `examples/fabric_migration/01_simple_filter.py ==================================`, `The routing agent pattern from DE-Context Kit.     Routes each query to the most`, `scripts/graphify_audit.py — KQLBridge Codebase Intelligence via Graphify =======`, `Full 7-step graphify pipeline on the KQLBridge source.`, `Fallback analysis without graphify — uses Python's ast module.` (+339 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `translate()` connect `Community 12` to `Community 1`, `Community 35`, `Community 4`, `Community 6`, `Community 7`, `Community 8`, `Community 39`, `Community 11`, `Community 16`, `Community 17`, `Community 19`, `Community 22`, `Community 23`, `Community 27`, `Community 28`, `Community 30`?**
  _High betweenness centrality (0.194) - this node is a cross-community bridge._
- **Why does `SparkSQLGenerator` connect `Community 0` to `Community 4`, `Community 5`, `Community 6`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Why does `PySparkGenerator` connect `Community 0` to `Community 1`, `Community 35`, `Community 4`, `Community 6`, `Community 8`, `Community 11`, `Community 12`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Are the 51 inferred relationships involving `SparkSQLGenerator` (e.g. with `ExplainResult` and `PySparkGenerator`) actually correct?**
  _`SparkSQLGenerator` has 51 INFERRED edges - model-reasoned connections that need verification._
- **Are the 67 inferred relationships involving `translate()` (e.g. with `route_query()` and `run_advanced_stress_tests()`) actually correct?**
  _`translate()` has 67 INFERRED edges - model-reasoned connections that need verification._
- **Are the 41 inferred relationships involving `PySparkGenerator` (e.g. with `ExplainResult` and `KQLQuery`) actually correct?**
  _`PySparkGenerator` has 41 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `TSQLGenerator` (e.g. with `ExplainResult` and `AgoExpr`) actually correct?**
  _`TSQLGenerator` has 17 INFERRED edges - model-reasoned connections that need verification._