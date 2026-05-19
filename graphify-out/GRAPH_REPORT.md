# Graph Report - kqlbridge  (2026-05-19)

## Corpus Check
- 27 files · ~19,039 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 460 nodes · 918 edges · 20 communities (19 shown, 1 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 135 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0f2ee97b`
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

## God Nodes (most connected - your core abstractions)
1. `SparkSQLGenerator` - 61 edges
2. `sql()` - 59 edges
3. `PySparkGenerator` - 25 edges
4. `ExplainResult` - 24 edges
5. `_build_expr()` - 21 edges
6. `LintIssue` - 20 edges
7. `TSQLGenerator` - 17 edges
8. `_build_bool_expr()` - 16 edges
9. `LintResult` - 15 edges
10. `translate()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `run()` --calls--> `parse()`  [INFERRED]
  run_stress_test.py → src/kqlbridge/parser.py
- `run()` --calls--> `smart_transpile()`  [INFERRED]
  run_stress_test.py → src/kqlbridge/smart.py
- `sql()` --calls--> `translate()`  [INFERRED]
  tests/test_operators.py → src/kqlbridge/__init__.py
- `score_one()` --calls--> `translate()`  [INFERRED]
  tests/eval/prepare.py → src/kqlbridge/__init__.py
- `run()` --calls--> `lint()`  [INFERRED]
  run_stress_test.py → src/kqlbridge/lint.py

## Communities (20 total, 1 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.07
Nodes (70): PySparkGenerator, Main entry point for PySpark generation., Experimental PySpark Generator.     Routes KQL AST nodes to executable PySpark D, Generates Spark SQL from a KQLQuery AST.      Usage:         gen = SparkSQLGener, SparkSQLGenerator, AggAvg, AggCount, AggCountIf (+62 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (18): lines(), test_operators.py — Per-Operator Unit Tests ====================================, Shorthand: translate KQL → Spark SQL., Split result into non-empty lines for structural checks., sql(), TestAgo, TestBin, TestCount (+10 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (25): generators/spark_sql.py — KQL AST → Spark SQL ==================================, # NOTE: do NOT clear where_clauses — WHERE filters from before, generators/tsql.py — KQL AST → T-SQL ===================================== AGENT, Generates T-SQL from a KQLQuery AST.     Inherits from SparkSQLGenerator — overr, TSQLGenerator, check(), is_supported(), kqlbridge — KQL to Spark SQL / T-SQL transpiler ================================ (+17 more)

### Community 3 - "Community 3"
Cohesion: 0.12
Nodes (37): BoolLit, ColumnRef, FloatLit, IntLit, A reference to a column: e.g. ServiceName, An integer literal: 100, A float literal: 3.14, A boolean literal: true / false (+29 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (30): 01 · `where` → `WHERE clause`, 02 · `project` → `SELECT columns`, 03 + 04 · `summarize` → `GROUP BY + aggregations`, 05 · `bin()` → `DATE_TRUNC / FLOOR`, 06 · `ago()` → `CURRENT_TIMESTAMP - INTERVAL`, 07 · `extend` → `SELECT *, computed_col AS expr`, 08 · `order by` / `sort by` → `ORDER BY`, 09 · `take` / `limit` → `LIMIT n` (+22 more)

### Community 5 - "Community 5"
Cohesion: 0.1
Nodes (17): examples/fabric_migration/01_simple_filter.py ==================================, The routing agent pattern from DE-Context Kit.     Routes each query to the most, route_query(), _check(), _explain(), _lint(), main(), _operators() (+9 more)

### Community 6 - "Community 6"
Cohesion: 0.1
Nodes (11): Returns (select_cols, group_by_cols).          Karpathy P5 — Jagged Intelligence, Render a single aggregation expression., KQL join → SQL INNER/LEFT/RIGHT/FULL JOIN.         Returns a 'table expression', KQL union T1, T2 or union (T1 | ...) → UNION ALL, Render bin(col, N<unit>) → Spark SQL timestamp bucketing.         - Hourly or co, Render a scalar expression to SQL., Map KQL built-in functions to Spark SQL equivalents.         Only functions need, Render a boolean expression to a SQL WHERE fragment. (+3 more)

### Community 7 - "Community 7"
Cohesion: 0.16
Nodes (21): is_clean(), lint(), LintIssue, lint.py — KQLBridge Semantic Drift Detector ====================================, LINT-03: bin(ts, 7d) buckets from Unix epoch, not calendar weeks., LINT-04: let bindings that reference earlier bindings may not resolve., LINT-05: extend col = col — self-assignment is ambiguous in Spark SQL., LINT-06: distinct * after project returns same rows as project alone. (+13 more)

### Community 8 - "Community 8"
Cohesion: 0.1
Nodes (19): Architecture, CLI, code:python (from kqlbridge import translate), code:bash (pip install kqlbridge), code:python (from kqlbridge import translate, detect_operators, is_suppor), code:bash (# Translate to Spark SQL (default)), code:bash (python tests/eval/prepare.py), code:block6 (KQL input) (+11 more)

### Community 9 - "Community 9"
Cohesion: 0.12
Nodes (15): AutoResearch Mapping, BIT Loop Cadence, Bloat Audit Checklist (run after every successful Build), code:block1 (prepare.py → SCORE: {pct:.1f}% ({pass}/{total})), code:block2 (src/kqlbridge/parser.py), code:block3 (tests/eval/prepare.py       # 🔒 LOCKED oracle — the eval scr), code:block4 (tests/eval/prepare.py returns SCORE ≥ 85.0%), code:block5 (□ Can any 10+ line block become a named function?) (+7 more)

### Community 10 - "Community 10"
Cohesion: 0.29
Nodes (13): _annotate_bin(), _annotate_op(), _annotate_query(), _annotate_where(), _build_annotated_sql(), explain(), _expr_note(), explain.py — KQLBridge Translation Annotator =================================== (+5 more)

### Community 11 - "Community 11"
Cohesion: 0.15
Nodes (12): `bag_unpack()`, code:kql (// No SQL equivalent — keep in KQL engine), code:python (from kqlbridge import is_supported, check), Deferred to v0.2, How to Handle Unsupported Operators, `ipv4_is_in_range()` / `ipv4_compare()`, `make-series`, Permanently Out of Scope (+4 more)

### Community 12 - "Community 12"
Cohesion: 0.24
Nodes (10): _canonical_match(), _canonicalize(), _is_syntactically_valid(), main(), prepare.py — KQLBridge Eval Oracle =================================== LOCKED FI, Check structural equivalence via canonical form., Check that the generated SQL is parseable by sqlglot as Spark SQL., Score a single benchmark case.      Returns (score: int, failure_reason: Optiona (+2 more)

### Community 13 - "Community 13"
Cohesion: 0.17
Nodes (11): Bug Reports, Code Style, code:block1 (tests/eval/prepare.py       # Eval oracle — LOCKED), code:bash (# 1. Fork and clone), code:block3 (**KQL input:** `AppLogs | where ...`), Contributing to KQLBridge, How to Contribute, License (+3 more)

### Community 14 - "Community 14"
Cohesion: 0.29
Nodes (9): _check_architecture_rules(), scripts/graphify_audit.py — KQLBridge Codebase Intelligence via Graphify =======, Fallback analysis without graphify — uses Python's ast module., Karpathy Principle 6 bloat audit checklist — run after every Tune phase., Check architectural invariants for the KQLBridge codebase.     These rules shoul, Full 7-step graphify pipeline on the KQLBridge source., _run_bloat_audit(), run_graphify_pipeline() (+1 more)

### Community 15 - "Community 15"
Cohesion: 0.25
Nodes (7): 1. `has_any()` Operator, 2. `percentile()` Aggregation, 3. `make_list()` Aggregation, 4. `serialize` and `prev()` Window Functions, 🛠 Implementation Cadence (v0.7), KQLBridge Roadmap — v0.7 Release & Subsequent PR Plan, 📋 Scheduled Features

### Community 16 - "Community 16"
Cohesion: 0.29
Nodes (6): 2026-05-16 — Session 0: Repo scaffold, Bloat Audit History, Current Eval Score, Operator Coverage, Operator Status — KQLBridge v0.1, Session Log

## Knowledge Gaps
- **141 isolated node(s):** `examples/fabric_migration/01_simple_filter.py ==================================`, `The routing agent pattern from DE-Context Kit.     Routes each query to the most`, `scripts/graphify_audit.py — KQLBridge Codebase Intelligence via Graphify =======`, `Full 7-step graphify pipeline on the KQLBridge source.`, `Fallback analysis without graphify — uses Python's ast module.` (+136 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `translate()` connect `Community 5` to `Community 1`, `Community 2`, `Community 3`, `Community 12`?**
  _High betweenness centrality (0.242) - this node is a cross-community bridge._
- **Why does `sql()` connect `Community 1` to `Community 5`?**
  _High betweenness centrality (0.202) - this node is a cross-community bridge._
- **Why does `SparkSQLGenerator` connect `Community 0` to `Community 2`, `Community 3`, `Community 6`?**
  _High betweenness centrality (0.109) - this node is a cross-community bridge._
- **Are the 42 inferred relationships involving `SparkSQLGenerator` (e.g. with `ExplainResult` and `PySparkGenerator`) actually correct?**
  _`SparkSQLGenerator` has 42 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `PySparkGenerator` (e.g. with `KQLQuery` and `ProjectOp`) actually correct?**
  _`PySparkGenerator` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `ExplainResult` (e.g. with `KQLQuery` and `WhereOp`) actually correct?**
  _`ExplainResult` has 21 INFERRED edges - model-reasoned connections that need verification._
- **What connects `examples/fabric_migration/01_simple_filter.py ==================================`, `The routing agent pattern from DE-Context Kit.     Routes each query to the most`, `scripts/graphify_audit.py — KQLBridge Codebase Intelligence via Graphify =======` to the rest of the system?**
  _141 weakly-connected nodes found - possible documentation gaps or missing edges._