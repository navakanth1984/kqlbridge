# Graph Report - kqlbridge  (2026-05-19)

## Corpus Check
- 28 files · ~21,761 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 559 nodes · 1088 edges · 21 communities (20 shown, 1 thin omitted)
- Extraction: 83% EXTRACTED · 17% INFERRED · 0% AMBIGUOUS · INFERRED: 181 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8db6021a`
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

## God Nodes (most connected - your core abstractions)
1. `SparkSQLGenerator` - 70 edges
2. `sql()` - 61 edges
3. `PySparkGenerator` - 45 edges
4. `TSQLGenerator` - 33 edges
5. `ExplainResult` - 24 edges
6. `translate()` - 23 edges
7. `parse()` - 22 edges
8. `_build_expr()` - 22 edges
9. `LintIssue` - 20 edges
10. `_build_bool_expr()` - 17 edges

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

## Communities (21 total, 1 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (62): # NOTE: do NOT clear where_clauses — WHERE filters from before, Generates T-SQL from a KQLQuery AST.     Inherits from SparkSQLGenerator — overr, Generates T-SQL from a KQLQuery AST.     Inherits from SparkSQLGenerator — overr, TSQLGenerator, AggAvg, AggCount, AggCountIf, AggDCount (+54 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (17): lines(), test_operators.py — Per-Operator Unit Tests ====================================, Shorthand: translate KQL → Spark SQL., Split result into non-empty lines for structural checks., sql(), TestAgo, TestBin, TestCount (+9 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (39): Walk the pipe operators and accumulate SQL clause fragments.         The assembl, Walk the pipe operators and accumulate SQL clause fragments.         The assembl, Returns (select_cols, group_by_cols).          Karpathy P5 — Jagged Intelligence, Returns (select_cols, group_by_cols).          Karpathy P5 — Jagged Intelligence, Returns (select_cols, group_by_cols).          Karpathy P5 — Jagged Intelligence, Returns (select_cols, group_by_cols).          Karpathy P5 — Jagged Intelligence, Render a single aggregation expression., Render a single aggregation expression. (+31 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (50): PySparkGenerator, Main entry point for PySpark generation., Experimental PySpark Generator.     Routes KQL AST nodes to executable PySpark D, BinGroup, DistinctOp, ExtendOp, LogicalOp, Negation (+42 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (27): examples/fabric_migration/01_simple_filter.py ==================================, The routing agent pattern from DE-Context Kit.     Routes each query to the most, route_query(), _check(), _explain(), _lint(), main(), _operators() (+19 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (48): CountOp, JoinOp, KQLQuery, PlainGroup, | join kind=inner (RightTable | ...) on key, | union T2, T3  or  | union (T2 | where ...), T3, | join kind=inner (RightTable | ...) on key, | union T2, T3  or  | union (T2 | where ...), T3 (+40 more)

### Community 6 - "Community 6"
Cohesion: 0.06
Nodes (30): 01 · `where` → `WHERE clause`, 02 · `project` → `SELECT columns`, 03 + 04 · `summarize` → `GROUP BY + aggregations`, 05 · `bin()` → `DATE_TRUNC / FLOOR`, 06 · `ago()` → `CURRENT_TIMESTAMP - INTERVAL`, 07 · `extend` → `SELECT *, computed_col AS expr`, 08 · `order by` / `sort by` → `ORDER BY`, 09 · `take` / `limit` → `LIMIT n` (+22 more)

### Community 7 - "Community 7"
Cohesion: 0.11
Nodes (14): generators/spark_sql.py — KQL AST → Spark SQL ==================================, # NOTE: do NOT clear where_clauses — WHERE filters from before, # NOTE: do NOT clear where_clauses — WHERE filters from before, generators/tsql.py — KQL AST → T-SQL ===================================== AGENT, check(), is_supported(), kqlbridge — KQL to Spark SQL / T-SQL transpiler ================================, Return True if the query can be fully translated to Spark SQL.      Queries with (+6 more)

### Community 8 - "Community 8"
Cohesion: 0.1
Nodes (19): Architecture, CLI, code:python (from kqlbridge import translate), code:bash (pip install kqlbridge), code:python (from kqlbridge import translate, detect_operators, is_suppor), code:bash (# Translate to Spark SQL (default)), code:bash (python tests/eval/prepare.py), code:block6 (KQL input) (+11 more)

### Community 9 - "Community 9"
Cohesion: 0.12
Nodes (16): 1. `has_any()` Operator, 1. Robust JSON Traversal (`parse_json(col).field`), 2. Array Unnesting & Explode (`mv-expand col`), 2. `percentile()` Aggregation, 3. `make_list()` Aggregation, 3. Multi-Branch Evaluation (`case(c1, v1, c2, v2, ..., default)`), 4. `serialize` and `prev()` Window Functions, 4. Threat Intelligence: Private IP Lookup (`ipv4_is_private(ip)`) (+8 more)

### Community 10 - "Community 10"
Cohesion: 0.28
Nodes (14): _annotate_bin(), _annotate_op(), _annotate_query(), _annotate_where(), _build_annotated_sql(), explain(), ExplainResult, _expr_note() (+6 more)

### Community 11 - "Community 11"
Cohesion: 0.12
Nodes (15): AutoResearch Mapping, BIT Loop Cadence, Bloat Audit Checklist (run after every successful Build), code:block1 (prepare.py → SCORE: {pct:.1f}% ({pass}/{total})), code:block2 (src/kqlbridge/parser.py), code:block3 (tests/eval/prepare.py       # 🔒 LOCKED oracle — the eval scr), code:block4 (tests/eval/prepare.py returns SCORE ≥ 85.0%), code:block5 (□ Can any 10+ line block become a named function?) (+7 more)

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

### Community 17 - "Community 17"
Cohesion: 0.29
Nodes (6): 2026-05-16 — Session 0: Repo scaffold, Bloat Audit History, Current Eval Score, Operator Coverage, Operator Status — KQLBridge v0.1, Session Log

## Knowledge Gaps
- **201 isolated node(s):** `examples/fabric_migration/01_simple_filter.py ==================================`, `The routing agent pattern from DE-Context Kit.     Routes each query to the most`, `scripts/graphify_audit.py — KQLBridge Codebase Intelligence via Graphify =======`, `Full 7-step graphify pipeline on the KQLBridge source.`, `Fallback analysis without graphify — uses Python's ast module.` (+196 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SparkSQLGenerator` connect `Community 2` to `Community 0`, `Community 3`, `Community 5`, `Community 7`, `Community 10`?**
  _High betweenness centrality (0.201) - this node is a cross-community bridge._
- **Why does `PySparkGenerator` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 4`, `Community 5`, `Community 7`?**
  _High betweenness centrality (0.162) - this node is a cross-community bridge._
- **Why does `translate()` connect `Community 4` to `Community 0`, `Community 1`, `Community 5`, `Community 7`, `Community 14`?**
  _High betweenness centrality (0.115) - this node is a cross-community bridge._
- **Are the 46 inferred relationships involving `SparkSQLGenerator` (e.g. with `ExplainResult` and `PySparkGenerator`) actually correct?**
  _`SparkSQLGenerator` has 46 INFERRED edges - model-reasoned connections that need verification._
- **Are the 37 inferred relationships involving `PySparkGenerator` (e.g. with `KQLQuery` and `ProjectOp`) actually correct?**
  _`PySparkGenerator` has 37 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `TSQLGenerator` (e.g. with `ExplainResult` and `AgoExpr`) actually correct?**
  _`TSQLGenerator` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `ExplainResult` (e.g. with `KQLQuery` and `WhereOp`) actually correct?**
  _`ExplainResult` has 21 INFERRED edges - model-reasoned connections that need verification._