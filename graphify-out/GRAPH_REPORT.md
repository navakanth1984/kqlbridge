# Graph Report - kqlbridge  (2026-05-19)

## Corpus Check
- 26 files · ~18,669 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 501 nodes · 840 edges · 24 communities (23 shown, 1 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 137 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f9852a6b`
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

## God Nodes (most connected - your core abstractions)
1. `SparkSQLGenerator` - 61 edges
2. `sql()` - 59 edges
3. `PySparkGenerator` - 26 edges
4. `ExplainResult` - 23 edges
5. `_build_expr()` - 20 edges
6. `LintIssue` - 19 edges
7. `translate()` - 17 edges
8. `TSQLGenerator` - 16 edges
9. `_build_bool_expr()` - 15 edges
10. `TestWhere` - 15 edges

## Surprising Connections (you probably didn't know these)
- `run()` --calls--> `lint()`  [INFERRED]
  run_stress_test.py → src/kqlbridge/lint.py
- `run()` --calls--> `smart_transpile()`  [INFERRED]
  run_stress_test.py → src/kqlbridge/smart.py
- `run()` --calls--> `translate()`  [INFERRED]
  run_stress_test.py → src/kqlbridge/__init__.py
- `route_query()` --calls--> `detect_operators()`  [INFERRED]
  examples/fabric_migration/01_simple_filter.py → src/kqlbridge/__init__.py
- `route_query()` --calls--> `translate()`  [INFERRED]
  examples/fabric_migration/01_simple_filter.py → src/kqlbridge/__init__.py

## Communities (24 total, 1 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (18): lines(), test_operators.py — Per-Operator Unit Tests ====================================, Shorthand: translate KQL → Spark SQL., Split result into non-empty lines for structural checks., sql(), TestAgo, TestBin, TestCount (+10 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (68): AggAvg, AggCount, AggCountIf, AggDCount, AggMax, AggMin, AggSum, BinaryOp (+60 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (47): PySparkGenerator, Main entry point for PySpark generation., Main entry point for PySpark generation., Main entry point for PySpark generation., Experimental PySpark Generator.     Routes KQL AST nodes to executable PySpark D, Experimental PySpark Generator.     Routes KQL AST nodes to executable PySpark D, Experimental PySpark Generator.     Routes KQL AST nodes to executable PySpark D, BinGroup (+39 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (29): Returns (select_cols, group_by_cols).          Karpathy P5 — Jagged Intelligence, Returns (select_cols, group_by_cols).          Karpathy P5 — Jagged Intelligence, Render a single aggregation expression., KQL join → SQL INNER/LEFT/RIGHT/FULL JOIN.         Returns a 'table expression', Render a single aggregation expression., KQL union T1, T2, T3 → SELECT * FROM T1 UNION ALL SELECT * FROM T2 ..., Render bin(col, N<unit>) → Spark SQL timestamp bucketing.         - Hourly or co, KQL join → SQL INNER/LEFT/RIGHT/FULL JOIN.         Returns a 'table expression' (+21 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (30): 01 · `where` → `WHERE clause`, 02 · `project` → `SELECT columns`, 03 + 04 · `summarize` → `GROUP BY + aggregations`, 05 · `bin()` → `DATE_TRUNC / FLOOR`, 06 · `ago()` → `CURRENT_TIMESTAMP - INTERVAL`, 07 · `extend` → `SELECT *, computed_col AS expr`, 08 · `order by` / `sort by` → `ORDER BY`, 09 · `take` / `limit` → `LIMIT n` (+22 more)

### Community 5 - "Community 5"
Cohesion: 0.09
Nodes (28): CountOp, JoinOp, KQLQuery, LetBinding, | join kind=inner (RightTable | ...) on key, | join kind=inner (RightTable | ...) on key, | union T2, T3  or  | union (T2 | where ...), T3, let errors = AppLogs | where Level == 'Error'; (+20 more)

### Community 6 - "Community 6"
Cohesion: 0.1
Nodes (22): Generates T-SQL from a KQLQuery AST.     Inherits from SparkSQLGenerator — overr, TSQLGenerator, AgoExpr, BinExpr, KQL ago(1h) → CURRENT_TIMESTAMP - INTERVAL '1 hours, KQL bin(col, 1h) → DATE_TRUNC('hour', col), KQL ago(1h) → CURRENT_TIMESTAMP - INTERVAL '1 hours, KQL bin(col, 1h) → DATE_TRUNC('hour', col) (+14 more)

### Community 7 - "Community 7"
Cohesion: 0.09
Nodes (23): Access Control, Architecture, CLI, code:python (from kqlbridge import translate), code:bash (pip install kqlbridge), code:python (from kqlbridge import translate, detect_operators, is_suppor), code:bash (# Translate to Spark SQL (default)), code:bash (python tests/eval/prepare.py) (+15 more)

### Community 8 - "Community 8"
Cohesion: 0.17
Nodes (14): _canonical_match(), _canonicalize(), _is_syntactically_valid(), main(), prepare.py — KQLBridge Eval Oracle =================================== LOCKED FI, Check structural equivalence via canonical form., Score a single benchmark case.      Returns (score: int, failure_reason: Optiona, Check that the generated SQL is parseable by sqlglot as Spark SQL. (+6 more)

### Community 9 - "Community 9"
Cohesion: 0.12
Nodes (15): AutoResearch Mapping, BIT Loop Cadence, Bloat Audit Checklist (run after every successful Build), code:block1 (prepare.py → SCORE: {pct:.1f}% ({pass}/{total})), code:block2 (src/kqlbridge/parser.py), code:block3 (tests/eval/prepare.py       # 🔒 LOCKED oracle — the eval scr), code:block4 (tests/eval/prepare.py returns SCORE ≥ 85.0%), code:block5 (□ Can any 10+ line block become a named function?) (+7 more)

### Community 10 - "Community 10"
Cohesion: 0.17
Nodes (9): generators/spark_sql.py — KQL AST → Spark SQL ==================================, # NOTE: do NOT clear where_clauses — WHERE filters from before, # NOTE: do NOT clear where_clauses — WHERE filters from before, generators/tsql.py — KQL AST → T-SQL ===================================== AGENT, kqlbridge — KQL to Spark SQL / T-SQL transpiler ================================, analyze_ast(), Intelligent compiler endpoint that parses the query, analyzes the AST,      and, AST Analyzer that scores complexity and structural intent to route     to the op (+1 more)

### Community 11 - "Community 11"
Cohesion: 0.15
Nodes (12): `bag_unpack()`, code:kql (// No SQL equivalent — keep in KQL engine), code:python (from kqlbridge import is_supported, check), Deferred to v0.2, How to Handle Unsupported Operators, `ipv4_is_in_range()` / `ipv4_compare()`, `make-series`, Permanently Out of Scope (+4 more)

### Community 12 - "Community 12"
Cohesion: 0.17
Nodes (11): Bug Reports, Code Style, code:block1 (tests/eval/prepare.py       # Eval oracle — LOCKED), code:bash (# 1. Fork and clone), code:block3 (**KQL input:** `AppLogs | where ...`), Contributing to KQLBridge, How to Contribute, License (+3 more)

### Community 13 - "Community 13"
Cohesion: 0.27
Nodes (5): Translate a KQL query string to the target SQL dialect.      Args:         kql:, Translate a KQL query string to the target SQL dialect.      Args:         kql:, Translate a KQL query string to the target SQL dialect.      Args:         kql:, translate(), TestCommunityFunctions

### Community 14 - "Community 14"
Cohesion: 0.18
Nodes (11): check(), is_supported(), Return True if the query can be fully translated to Spark SQL.      Queries with, Return True if the query can be fully translated to Spark SQL.      Queries with, Parse and semantically validate a KQL query.      Returns a SemanticResult with:, Return True if the query can be fully translated to Spark SQL.      Queries with, Return True if the query can be fully translated to Spark SQL.      Queries with, Parse and semantically validate a KQL query.      Returns a SemanticResult with: (+3 more)

### Community 15 - "Community 15"
Cohesion: 0.18
Nodes (8): _check(), detect_operators(), Return the list of KQL operators used in a query string.      Useful for routing, Return the list of KQL operators used in a query string.      Useful for routing, Return the list of KQL operators used in a query string.      Useful for routing, Return the list of KQL operators used in a query string.      Useful for routing, Return the list of KQL operators used in a query string.      Useful for routing, TestPublicAPI

### Community 16 - "Community 16"
Cohesion: 0.29
Nodes (9): _check_architecture_rules(), scripts/graphify_audit.py — KQLBridge Codebase Intelligence via Graphify =======, Fallback analysis without graphify — uses Python's ast module., Karpathy Principle 6 bloat audit checklist — run after every Tune phase., Check architectural invariants for the KQLBridge codebase.     These rules shoul, Full 7-step graphify pipeline on the KQLBridge source., _run_bloat_audit(), run_graphify_pipeline() (+1 more)

### Community 17 - "Community 17"
Cohesion: 0.25
Nodes (4): _explain(), _lint(), cli.py — KQLBridge command-line interface ======================================, _translate()

### Community 18 - "Community 18"
Cohesion: 0.29
Nodes (6): get_parser(), _normalize_keywords(), parse(), Parse a KQL query string into a KQLQuery AST.     Keywords are normalized to low, Lowercase KQL keywords while preserving quoted string content., run()

### Community 19 - "Community 19"
Cohesion: 0.29
Nodes (6): 2026-05-16 — Session 0: Repo scaffold, Bloat Audit History, Current Eval Score, Operator Coverage, Operator Status — KQLBridge v0.1, Session Log

### Community 20 - "Community 20"
Cohesion: 0.5
Nodes (3): examples/fabric_migration/01_simple_filter.py ==================================, The routing agent pattern from DE-Context Kit.     Routes each query to the most, route_query()

## Knowledge Gaps
- **198 isolated node(s):** `examples/fabric_migration/01_simple_filter.py ==================================`, `The routing agent pattern from DE-Context Kit.     Routes each query to the most`, `scripts/graphify_audit.py — KQLBridge Codebase Intelligence via Graphify =======`, `Full 7-step graphify pipeline on the KQLBridge source.`, `Fallback analysis without graphify — uses Python's ast module.` (+193 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `translate()` connect `Community 13` to `Community 0`, `Community 8`, `Community 10`, `Community 15`, `Community 17`, `Community 18`, `Community 20`?**
  _High betweenness centrality (0.261) - this node is a cross-community bridge._
- **Why does `sql()` connect `Community 0` to `Community 13`?**
  _High betweenness centrality (0.202) - this node is a cross-community bridge._
- **Why does `SparkSQLGenerator` connect `Community 3` to `Community 1`, `Community 2`, `Community 5`, `Community 6`, `Community 10`?**
  _High betweenness centrality (0.186) - this node is a cross-community bridge._
- **Are the 42 inferred relationships involving `SparkSQLGenerator` (e.g. with `ExplainResult` and `PySparkGenerator`) actually correct?**
  _`SparkSQLGenerator` has 42 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `PySparkGenerator` (e.g. with `KQLQuery` and `ProjectOp`) actually correct?**
  _`PySparkGenerator` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `ExplainResult` (e.g. with `KQLQuery` and `WhereOp`) actually correct?**
  _`ExplainResult` has 21 INFERRED edges - model-reasoned connections that need verification._
- **What connects `examples/fabric_migration/01_simple_filter.py ==================================`, `The routing agent pattern from DE-Context Kit.     Routes each query to the most`, `scripts/graphify_audit.py — KQLBridge Codebase Intelligence via Graphify =======` to the rest of the system?**
  _198 weakly-connected nodes found - possible documentation gaps or missing edges._