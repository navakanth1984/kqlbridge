# Graph Report - kqlbridge  (2026-05-19)

## Corpus Check
- 28 files · ~19,626 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 487 nodes · 967 edges · 31 communities (21 shown, 10 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 156 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `680dc92f`
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

## God Nodes (most connected - your core abstractions)
1. `SparkSQLGenerator` - 61 edges
2. `sql()` - 61 edges
3. `PySparkGenerator` - 41 edges
4. `ExplainResult` - 24 edges
5. `_build_expr()` - 22 edges
6. `LintIssue` - 20 edges
7. `translate()` - 18 edges
8. `TSQLGenerator` - 17 edges
9. `parse()` - 16 edges
10. `_build_bool_expr()` - 16 edges

## Surprising Connections (you probably didn't know these)
- `run()` --calls--> `parse()`  [INFERRED]
  run_stress_test.py → src/kqlbridge/parser.py
- `run()` --calls--> `lint()`  [INFERRED]
  run_stress_test.py → src/kqlbridge/lint.py
- `sql()` --calls--> `translate()`  [INFERRED]
  tests/test_operators.py → src/kqlbridge/__init__.py
- `score_one()` --calls--> `translate()`  [INFERRED]
  tests/eval/prepare.py → src/kqlbridge/__init__.py
- `TestWhere` --uses--> `PySparkGenerator`  [INFERRED]
  tests/test_operators.py → src/kqlbridge/generators/pyspark.py

## Communities (31 total, 10 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.07
Nodes (79): Generates Spark SQL from a KQLQuery AST.      Usage:         gen = SparkSQLGener, SparkSQLGenerator, AggAvg, AggCount, AggCountIf, AggDCount, AggMax, AggMin (+71 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (30): generators/spark_sql.py — KQL AST → Spark SQL ==================================, # NOTE: do NOT clear where_clauses — WHERE filters from before, # NOTE: do NOT clear where_clauses — WHERE filters from before, generators/tsql.py — KQL AST → T-SQL ===================================== AGENT, Generates T-SQL from a KQLQuery AST.     Inherits from SparkSQLGenerator — overr, TSQLGenerator, _annotate_bin(), _annotate_op() (+22 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (21): Walk the pipe operators and accumulate SQL clause fragments.         The assembl, Returns (select_cols, group_by_cols).          Karpathy P5 — Jagged Intelligence, Returns (select_cols, group_by_cols).          Karpathy P5 — Jagged Intelligence, Render a single aggregation expression., Render a single aggregation expression., KQL join → SQL INNER/LEFT/RIGHT/FULL JOIN.         Returns a 'table expression', KQL join → SQL INNER/LEFT/RIGHT/FULL JOIN.         Returns a 'table expression', KQL union T1, T2 or union (T1 | ...) → UNION ALL (+13 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (23): examples/fabric_migration/01_simple_filter.py ==================================, The routing agent pattern from DE-Context Kit.     Routes each query to the most, route_query(), _check(), _explain(), _lint(), main(), _operators() (+15 more)

### Community 4 - "Community 4"
Cohesion: 0.14
Nodes (29): KQLQuery, The root AST node. Represents a complete KQL query.      let_bindings → will bec, _build_agg_item(), _build_agg_list(), _build_distinct(), _build_groupby_list(), _build_join(), _build_let() (+21 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (30): 01 · `where` → `WHERE clause`, 02 · `project` → `SELECT columns`, 03 + 04 · `summarize` → `GROUP BY + aggregations`, 05 · `bin()` → `DATE_TRUNC / FLOOR`, 06 · `ago()` → `CURRENT_TIMESTAMP - INTERVAL`, 07 · `extend` → `SELECT *, computed_col AS expr`, 08 · `order by` / `sort by` → `ORDER BY`, 09 · `take` / `limit` → `LIMIT n` (+22 more)

### Community 6 - "Community 6"
Cohesion: 0.18
Nodes (20): is_clean(), lint(), LintIssue, lint.py — KQLBridge Semantic Drift Detector ====================================, LINT-03: bin(ts, 7d) buckets from Unix epoch, not calendar weeks., LINT-04: let bindings that reference earlier bindings may not resolve., LINT-05: extend col = col — self-assignment is ambiguous in Spark SQL., LINT-06: distinct * after project returns same rows as project alone. (+12 more)

### Community 7 - "Community 7"
Cohesion: 0.1
Nodes (19): Architecture, CLI, code:python (from kqlbridge import translate), code:bash (pip install kqlbridge), code:python (from kqlbridge import translate, detect_operators, is_suppor), code:bash (# Translate to Spark SQL (default)), code:bash (python tests/eval/prepare.py), code:block6 (KQL input) (+11 more)

### Community 8 - "Community 8"
Cohesion: 0.21
Nodes (3): Shorthand: translate KQL → Spark SQL., sql(), TestWhere

### Community 9 - "Community 9"
Cohesion: 0.12
Nodes (15): AutoResearch Mapping, BIT Loop Cadence, Bloat Audit Checklist (run after every successful Build), code:block1 (prepare.py → SCORE: {pct:.1f}% ({pass}/{total})), code:block2 (src/kqlbridge/parser.py), code:block3 (tests/eval/prepare.py       # 🔒 LOCKED oracle — the eval scr), code:block4 (tests/eval/prepare.py returns SCORE ≥ 85.0%), code:block5 (□ Can any 10+ line block become a named function?) (+7 more)

### Community 10 - "Community 10"
Cohesion: 0.19
Nodes (4): PySparkGenerator, Main entry point for PySpark generation., Experimental PySpark Generator.     Routes KQL AST nodes to executable PySpark D, TestLet

### Community 11 - "Community 11"
Cohesion: 0.15
Nodes (5): lines(), test_operators.py — Per-Operator Unit Tests ====================================, Split result into non-empty lines for structural checks., TestCount, TestJoin

### Community 12 - "Community 12"
Cohesion: 0.15
Nodes (12): `bag_unpack()`, code:kql (// No SQL equivalent — keep in KQL engine), code:python (from kqlbridge import is_supported, check), Deferred to v0.2, How to Handle Unsupported Operators, `ipv4_is_in_range()` / `ipv4_compare()`, `make-series`, Permanently Out of Scope (+4 more)

### Community 13 - "Community 13"
Cohesion: 0.32
Nodes (10): check(), _check_let_bindings(), _check_pipes(), _check_summarize_rewrite(), is_supported(), semantic.py — KQLBridge Semantic Validator =====================================, Let bindings become CTEs. Circular references are not supported., Run semantic validation on a parsed KQLQuery.      Returns a SemanticResult with (+2 more)

### Community 14 - "Community 14"
Cohesion: 0.24
Nodes (10): _canonical_match(), _canonicalize(), _is_syntactically_valid(), main(), prepare.py — KQLBridge Eval Oracle =================================== LOCKED FI, Check structural equivalence via canonical form., Check that the generated SQL is parseable by sqlglot as Spark SQL., Score a single benchmark case.      Returns (score: int, failure_reason: Optiona (+2 more)

### Community 15 - "Community 15"
Cohesion: 0.17
Nodes (11): Bug Reports, Code Style, code:block1 (tests/eval/prepare.py       # Eval oracle — LOCKED), code:bash (# 1. Fork and clone), code:block3 (**KQL input:** `AppLogs | where ...`), Contributing to KQLBridge, How to Contribute, License (+3 more)

### Community 16 - "Community 16"
Cohesion: 0.29
Nodes (9): _check_architecture_rules(), scripts/graphify_audit.py — KQLBridge Codebase Intelligence via Graphify =======, Fallback analysis without graphify — uses Python's ast module., Karpathy Principle 6 bloat audit checklist — run after every Tune phase., Check architectural invariants for the KQLBridge codebase.     These rules shoul, Full 7-step graphify pipeline on the KQLBridge source., _run_bloat_audit(), run_graphify_pipeline() (+1 more)

### Community 18 - "Community 18"
Cohesion: 0.25
Nodes (7): 1. `has_any()` Operator, 2. `percentile()` Aggregation, 3. `make_list()` Aggregation, 4. `serialize` and `prev()` Window Functions, 🛠 Implementation Cadence (v0.7), KQLBridge Roadmap — v0.7 Release & Subsequent PR Plan, 📋 Scheduled Features

### Community 19 - "Community 19"
Cohesion: 0.29
Nodes (6): 2026-05-16 — Session 0: Repo scaffold, Bloat Audit History, Current Eval Score, Operator Coverage, Operator Status — KQLBridge v0.1, Session Log

## Knowledge Gaps
- **160 isolated node(s):** `examples/fabric_migration/01_simple_filter.py ==================================`, `The routing agent pattern from DE-Context Kit.     Routes each query to the most`, `scripts/graphify_audit.py — KQLBridge Codebase Intelligence via Graphify =======`, `Full 7-step graphify pipeline on the KQLBridge source.`, `Fallback analysis without graphify — uses Python's ast module.` (+155 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SparkSQLGenerator` connect `Community 0` to `Community 1`, `Community 2`, `Community 10`, `Community 4`?**
  _High betweenness centrality (0.165) - this node is a cross-community bridge._
- **Why does `PySparkGenerator` connect `Community 10` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 8`, `Community 11`, `Community 17`, `Community 20`, `Community 21`, `Community 22`, `Community 23`, `Community 24`, `Community 25`, `Community 26`, `Community 27`?**
  _High betweenness centrality (0.158) - this node is a cross-community bridge._
- **Why does `translate()` connect `Community 3` to `Community 1`, `Community 4`, `Community 8`, `Community 10`, `Community 14`?**
  _High betweenness centrality (0.122) - this node is a cross-community bridge._
- **Are the 42 inferred relationships involving `SparkSQLGenerator` (e.g. with `ExplainResult` and `PySparkGenerator`) actually correct?**
  _`SparkSQLGenerator` has 42 INFERRED edges - model-reasoned connections that need verification._
- **Are the 33 inferred relationships involving `PySparkGenerator` (e.g. with `KQLQuery` and `ProjectOp`) actually correct?**
  _`PySparkGenerator` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `ExplainResult` (e.g. with `KQLQuery` and `WhereOp`) actually correct?**
  _`ExplainResult` has 21 INFERRED edges - model-reasoned connections that need verification._
- **What connects `examples/fabric_migration/01_simple_filter.py ==================================`, `The routing agent pattern from DE-Context Kit.     Routes each query to the most`, `scripts/graphify_audit.py — KQLBridge Codebase Intelligence via Graphify =======` to the rest of the system?**
  _160 weakly-connected nodes found - possible documentation gaps or missing edges._