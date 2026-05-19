# Graph Report - kqlbridge  (2026-05-19)

## Corpus Check
- 31 files · ~24,336 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 629 nodes · 1178 edges · 23 communities (22 shown, 1 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 190 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `baf48cd5`
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

## God Nodes (most connected - your core abstractions)
1. `SparkSQLGenerator` - 70 edges
2. `sql()` - 61 edges
3. `PySparkGenerator` - 46 edges
4. `TSQLGenerator` - 33 edges
5. `translate()` - 29 edges
6. `ExplainResult` - 24 edges
7. `parse()` - 23 edges
8. `_build_expr()` - 23 edges
9. `LintIssue` - 20 edges
10. `_build_bool_expr()` - 17 edges

## Surprising Connections (you probably didn't know these)
- `run()` --calls--> `parse()`  [INFERRED]
  run_stress_test.py → src/kqlbridge/parser.py
- `run()` --calls--> `lint()`  [INFERRED]
  run_stress_test.py → src/kqlbridge/lint.py
- `route_query()` --calls--> `translate()`  [INFERRED]
  examples/fabric_migration/01_simple_filter.py → src/kqlbridge/__init__.py
- `run_advanced_stress_tests()` --calls--> `translate()`  [INFERRED]
  examples/market_pain_points/advanced_stress_tests.py → src/kqlbridge/__init__.py
- `run_market_stress_tests()` --calls--> `translate()`  [INFERRED]
  examples/market_pain_points/market_stress_tests.py → src/kqlbridge/__init__.py

## Communities (23 total, 1 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (17): lines(), test_operators.py — Per-Operator Unit Tests ====================================, Shorthand: translate KQL → Spark SQL., Split result into non-empty lines for structural checks., sql(), TestAgo, TestBin, TestCount (+9 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (57): Generates T-SQL from a KQLQuery AST.     Inherits from SparkSQLGenerator — overr, Generates T-SQL from a KQLQuery AST.     Inherits from SparkSQLGenerator — overr, TSQLGenerator, AggAvg, AggCount, AggCountIf, AggDCount, AggMakeList (+49 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (40): Walk the pipe operators and accumulate SQL clause fragments.         The assembl, Walk the pipe operators and accumulate SQL clause fragments.         The assembl, Returns (select_cols, group_by_cols).          Karpathy P5 — Jagged Intelligence, Returns (select_cols, group_by_cols).          Karpathy P5 — Jagged Intelligence, Returns (select_cols, group_by_cols).          Karpathy P5 — Jagged Intelligence, Returns (select_cols, group_by_cols).          Karpathy P5 — Jagged Intelligence, Render a single aggregation expression., Render a single aggregation expression. (+32 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (58): BoolLit, ColumnRef, ExtendOp, FloatLit, IntLit, PlainGroup, A reference to a column: e.g. ServiceName, | extend alias = expr (+50 more)

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (45): BinGroup, Comparison, DistinctOp, ProjectOp, col == 'Error', TimeGenerated > ago(1h), col == 'Error', TimeGenerated > ago(1h), has, contains, startswith, endswith, matches regex, has, contains, startswith, endswith, matches regex (+37 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (18): PySparkGenerator, Main entry point for PySpark generation., Experimental PySpark Generator.     Routes KQL AST nodes to executable PySpark D, LogicalOp, Negation, cond1 and cond2 / cond1 or cond2, cond1 and cond2 / cond1 or cond2, | summarize count() by ServiceName (+10 more)

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (25): generators/spark_sql.py — KQL AST → Spark SQL ==================================, # NOTE: do NOT clear where_clauses — WHERE filters from before, # NOTE: do NOT clear where_clauses — WHERE filters from before, # NOTE: do NOT clear where_clauses — WHERE filters from before, generators/tsql.py — KQL AST → T-SQL ===================================== AGENT, check(), is_supported(), kqlbridge — KQL to Spark SQL / T-SQL transpiler ================================ (+17 more)

### Community 7 - "Community 7"
Cohesion: 0.06
Nodes (33): 1. `format_datetime(col, format)` — Datetime Formatting, 1. `has_any()` Operator, 1. Multi-Line `let` + Scalar Expression Chaining, 1. Robust JSON Traversal (`parse_json(col).field`), 2. Array Unnesting & Explode (`mv-expand col`), 2. `percentile()` Aggregation, 2. `summarize ... by bin_auto(TimeGenerated)` — Auto-Bin Detection, 2. `tostring(col)` / `toint(col)` / `tolong(col)` / `todouble(col)` — Type Casting (+25 more)

### Community 8 - "Community 8"
Cohesion: 0.06
Nodes (30): 01 · `where` → `WHERE clause`, 02 · `project` → `SELECT columns`, 03 + 04 · `summarize` → `GROUP BY + aggregations`, 05 · `bin()` → `DATE_TRUNC / FLOOR`, 06 · `ago()` → `CURRENT_TIMESTAMP - INTERVAL`, 07 · `extend` → `SELECT *, computed_col AS expr`, 08 · `order by` / `sort by` → `ORDER BY`, 09 · `take` / `limit` → `LIMIT n` (+22 more)

### Community 9 - "Community 9"
Cohesion: 0.09
Nodes (23): examples/fabric_migration/01_simple_filter.py ==================================, The routing agent pattern from DE-Context Kit.     Routes each query to the most, route_query(), _check(), _explain(), _lint(), main(), _operators() (+15 more)

### Community 10 - "Community 10"
Cohesion: 0.09
Nodes (23): JoinOp, KQLQuery, | join kind=inner (RightTable | ...) on key, | union T2, T3  or  | union (T2 | where ...), T3, | join kind=inner (RightTable | ...) on key, | join kind=inner (RightTable | ...) on key, | union T2, T3  or  | union (T2 | where ...), T3, | union T2, T3  or  | union (T2 | where ...), T3 (+15 more)

### Community 11 - "Community 11"
Cohesion: 0.1
Nodes (19): Architecture, CLI, code:python (from kqlbridge import translate), code:bash (pip install kqlbridge), code:python (from kqlbridge import translate, detect_operators, is_suppor), code:bash (# Translate to Spark SQL (default)), code:bash (python tests/eval/prepare.py), code:block6 (KQL input) (+11 more)

### Community 12 - "Community 12"
Cohesion: 0.28
Nodes (14): _annotate_bin(), _annotate_op(), _annotate_query(), _annotate_where(), _build_annotated_sql(), explain(), ExplainResult, _expr_note() (+6 more)

### Community 13 - "Community 13"
Cohesion: 0.12
Nodes (15): AutoResearch Mapping, BIT Loop Cadence, Bloat Audit Checklist (run after every successful Build), code:block1 (prepare.py → SCORE: {pct:.1f}% ({pass}/{total})), code:block2 (src/kqlbridge/parser.py), code:block3 (tests/eval/prepare.py       # 🔒 LOCKED oracle — the eval scr), code:block4 (tests/eval/prepare.py returns SCORE ≥ 85.0%), code:block5 (□ Can any 10+ line block become a named function?) (+7 more)

### Community 14 - "Community 14"
Cohesion: 0.15
Nodes (12): `bag_unpack()`, code:kql (// No SQL equivalent — keep in KQL engine), code:python (from kqlbridge import is_supported, check), Deferred to v0.2, How to Handle Unsupported Operators, `ipv4_is_in_range()` / `ipv4_compare()`, `make-series`, Permanently Out of Scope (+4 more)

### Community 15 - "Community 15"
Cohesion: 0.24
Nodes (10): _canonical_match(), _canonicalize(), _is_syntactically_valid(), main(), prepare.py — KQLBridge Eval Oracle =================================== LOCKED FI, Check structural equivalence via canonical form., Check that the generated SQL is parseable by sqlglot as Spark SQL., Score a single benchmark case.      Returns (score: int, failure_reason: Optiona (+2 more)

### Community 16 - "Community 16"
Cohesion: 0.17
Nodes (11): Bug Reports, Code Style, code:block1 (tests/eval/prepare.py       # Eval oracle — LOCKED), code:bash (# 1. Fork and clone), code:block3 (**KQL input:** `AppLogs | where ...`), Contributing to KQLBridge, How to Contribute, License (+3 more)

### Community 17 - "Community 17"
Cohesion: 0.29
Nodes (9): _check_architecture_rules(), scripts/graphify_audit.py — KQLBridge Codebase Intelligence via Graphify =======, Fallback analysis without graphify — uses Python's ast module., Karpathy Principle 6 bloat audit checklist — run after every Tune phase., Check architectural invariants for the KQLBridge codebase.     These rules shoul, Full 7-step graphify pipeline on the KQLBridge source., _run_bloat_audit(), run_graphify_pipeline() (+1 more)

### Community 18 - "Community 18"
Cohesion: 0.25
Nodes (7): 1. The "SQL Brain" Join Trap, 2. Post-Aggregation Filtering (HAVING vs WHERE), 3. T-SQL Compatibility & Semantic Drift, 4. Time-Series Analysis at Scale, 5. Query Complexity & Nesting, Known Limitations (Market Gaps), KQLBridge Market Research: Real-World Migration Pain Points

### Community 19 - "Community 19"
Cohesion: 0.29
Nodes (6): 2026-05-16 — Session 0: Repo scaffold, Bloat Audit History, Current Eval Score, Operator Coverage, Operator Status — KQLBridge v0.1, Session Log

## Knowledge Gaps
- **252 isolated node(s):** `examples/fabric_migration/01_simple_filter.py ==================================`, `The routing agent pattern from DE-Context Kit.     Routes each query to the most`, `scripts/graphify_audit.py — KQLBridge Codebase Intelligence via Graphify =======`, `Full 7-step graphify pipeline on the KQLBridge source.`, `Fallback analysis without graphify — uses Python's ast module.` (+247 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SparkSQLGenerator` connect `Community 2` to `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 10`, `Community 12`?**
  _High betweenness centrality (0.188) - this node is a cross-community bridge._
- **Why does `PySparkGenerator` connect `Community 5` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 6`, `Community 10`?**
  _High betweenness centrality (0.153) - this node is a cross-community bridge._
- **Why does `translate()` connect `Community 5` to `Community 0`, `Community 3`, `Community 6`, `Community 9`, `Community 15`?**
  _High betweenness centrality (0.107) - this node is a cross-community bridge._
- **Are the 46 inferred relationships involving `SparkSQLGenerator` (e.g. with `ExplainResult` and `PySparkGenerator`) actually correct?**
  _`SparkSQLGenerator` has 46 INFERRED edges - model-reasoned connections that need verification._
- **Are the 38 inferred relationships involving `PySparkGenerator` (e.g. with `KQLQuery` and `ProjectOp`) actually correct?**
  _`PySparkGenerator` has 38 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `TSQLGenerator` (e.g. with `ExplainResult` and `AgoExpr`) actually correct?**
  _`TSQLGenerator` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `translate()` (e.g. with `route_query()` and `run_advanced_stress_tests()`) actually correct?**
  _`translate()` has 25 INFERRED edges - model-reasoned connections that need verification._