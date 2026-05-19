# Graph Report - kqlbridge  (2026-05-19)

## Corpus Check
- 26 files · ~17,889 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 479 nodes · 796 edges · 24 communities (23 shown, 1 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 125 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `94f2e3ac`
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
1. `SparkSQLGenerator` - 59 edges
2. `sql()` - 57 edges
3. `ExplainResult` - 23 edges
4. `_build_expr()` - 20 edges
5. `LintIssue` - 19 edges
6. `PySparkGenerator` - 16 edges
7. `TSQLGenerator` - 16 edges
8. `_build_bool_expr()` - 15 edges
9. `LintResult` - 14 edges
10. `v0.1 Scope — 14 Operators` - 14 edges

## Surprising Connections (you probably didn't know these)
- `run()` --calls--> `lint()`  [INFERRED]
  run_stress_test.py → src/kqlbridge/lint.py
- `run()` --calls--> `smart_transpile()`  [INFERRED]
  run_stress_test.py → src/kqlbridge/smart.py
- `route_query()` --calls--> `detect_operators()`  [INFERRED]
  examples/fabric_migration/01_simple_filter.py → src/kqlbridge/__init__.py
- `route_query()` --calls--> `translate()`  [INFERRED]
  examples/fabric_migration/01_simple_filter.py → src/kqlbridge/__init__.py
- `sql()` --calls--> `translate()`  [INFERRED]
  tests/test_operators.py → src/kqlbridge/__init__.py

## Communities (24 total, 1 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (85): Generates Spark SQL from a KQLQuery AST.      Usage:         gen = SparkSQLGener, Generates Spark SQL from a KQLQuery AST.      Usage:         gen = SparkSQLGener, SparkSQLGenerator, AggAvg, AggCount, AggCountIf, AggDCount, AggMax (+77 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (18): lines(), test_operators.py — Per-Operator Unit Tests ====================================, Shorthand: translate KQL → Spark SQL., Split result into non-empty lines for structural checks., sql(), TestAgo, TestBin, TestCount (+10 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (44): PySparkGenerator, Main entry point for PySpark generation., Main entry point for PySpark generation., Experimental PySpark Generator.     Routes KQL AST nodes to executable PySpark D, Experimental PySpark Generator.     Routes KQL AST nodes to executable PySpark D, BinGroup, DistinctOp, ExtendOp (+36 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (22): Returns (select_cols, group_by_cols).          Karpathy P5 — Jagged Intelligence, Returns (select_cols, group_by_cols).          Karpathy P5 — Jagged Intelligence, Render a single aggregation expression., KQL join → SQL INNER/LEFT/RIGHT/FULL JOIN.         Returns a 'table expression', Render a single aggregation expression., KQL union T1, T2, T3 → SELECT * FROM T1 UNION ALL SELECT * FROM T2 ..., Render bin(col, N<unit>) → Spark SQL timestamp bucketing.         - Hourly or co, KQL join → SQL INNER/LEFT/RIGHT/FULL JOIN.         Returns a 'table expression' (+14 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (30): 01 · `where` → `WHERE clause`, 02 · `project` → `SELECT columns`, 03 + 04 · `summarize` → `GROUP BY + aggregations`, 05 · `bin()` → `DATE_TRUNC / FLOOR`, 06 · `ago()` → `CURRENT_TIMESTAMP - INTERVAL`, 07 · `extend` → `SELECT *, computed_col AS expr`, 08 · `order by` / `sort by` → `ORDER BY`, 09 · `take` / `limit` → `LIMIT n` (+22 more)

### Community 5 - "Community 5"
Cohesion: 0.11
Nodes (22): JoinOp, KQLQuery, LetBinding, | join kind=inner (RightTable | ...) on key, | join kind=inner (RightTable | ...) on key, let errors = AppLogs | where Level == 'Error';, The root AST node. Represents a complete KQL query.      let_bindings → will bec, let errors = AppLogs | where Level == 'Error'; (+14 more)

### Community 6 - "Community 6"
Cohesion: 0.09
Nodes (23): Access Control, Architecture, CLI, code:python (from kqlbridge import translate), code:bash (pip install kqlbridge), code:python (from kqlbridge import translate, detect_operators, is_suppor), code:bash (# Translate to Spark SQL (default)), code:python (# ⚠️ If user-controlled KQL is translated and executed dynam) (+15 more)

### Community 7 - "Community 7"
Cohesion: 0.13
Nodes (16): Generates T-SQL from a KQLQuery AST.     Inherits from SparkSQLGenerator — overr, TSQLGenerator, _explain(), _annotate_bin(), _annotate_op(), _annotate_query(), _annotate_where(), _build_annotated_sql() (+8 more)

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
Cohesion: 0.18
Nodes (11): _translate(), Translate a KQL query string to the target SQL dialect.      Args:         kql:, Translate a KQL query string to the target SQL dialect.      Args:         kql:, Translate a KQL query string to the target SQL dialect.      Args:         kql:, translate(), get_parser(), _normalize_keywords(), parse() (+3 more)

### Community 13 - "Community 13"
Cohesion: 0.17
Nodes (11): Bug Reports, Code Style, code:block1 (tests/eval/prepare.py       # Eval oracle — LOCKED), code:bash (# 1. Fork and clone), code:block3 (**KQL input:** `AppLogs | where ...`), Contributing to KQLBridge, How to Contribute, License (+3 more)

### Community 14 - "Community 14"
Cohesion: 0.29
Nodes (9): _check_architecture_rules(), scripts/graphify_audit.py — KQLBridge Codebase Intelligence via Graphify =======, Fallback analysis without graphify — uses Python's ast module., Karpathy Principle 6 bloat audit checklist — run after every Tune phase., Check architectural invariants for the KQLBridge codebase.     These rules shoul, Full 7-step graphify pipeline on the KQLBridge source., _run_bloat_audit(), run_graphify_pipeline() (+1 more)

### Community 15 - "Community 15"
Cohesion: 0.22
Nodes (6): detect_operators(), Return the list of KQL operators used in a query string.      Useful for routing, Return the list of KQL operators used in a query string.      Useful for routing, Return the list of KQL operators used in a query string.      Useful for routing, Return the list of KQL operators used in a query string.      Useful for routing, TestPublicAPI

### Community 16 - "Community 16"
Cohesion: 0.29
Nodes (3): _check(), _lint(), cli.py — KQLBridge command-line interface ======================================

### Community 17 - "Community 17"
Cohesion: 0.29
Nodes (6): 2026-05-16 — Session 0: Repo scaffold, Bloat Audit History, Current Eval Score, Operator Coverage, Operator Status — KQLBridge v0.1, Session Log

### Community 18 - "Community 18"
Cohesion: 0.4
Nodes (5): is_supported(), Return True if the query can be fully translated to Spark SQL.      Queries with, Return True if the query can be fully translated to Spark SQL.      Queries with, Return True if the query can be fully translated to Spark SQL.      Queries with, Return True if the query can be fully translated to Spark SQL.      Queries with

### Community 19 - "Community 19"
Cohesion: 0.4
Nodes (5): check(), Parse and semantically validate a KQL query.      Returns a SemanticResult with:, Parse and semantically validate a KQL query.      Returns a SemanticResult with:, Parse and semantically validate a KQL query.      Returns a SemanticResult with:, Parse and semantically validate a KQL query.      Returns a SemanticResult with:

### Community 20 - "Community 20"
Cohesion: 0.5
Nodes (3): examples/fabric_migration/01_simple_filter.py ==================================, The routing agent pattern from DE-Context Kit.     Routes each query to the most, route_query()

## Knowledge Gaps
- **191 isolated node(s):** `examples/fabric_migration/01_simple_filter.py ==================================`, `The routing agent pattern from DE-Context Kit.     Routes each query to the most`, `scripts/graphify_audit.py — KQLBridge Codebase Intelligence via Graphify =======`, `Full 7-step graphify pipeline on the KQLBridge source.`, `Fallback analysis without graphify — uses Python's ast module.` (+186 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `translate()` connect `Community 12` to `Community 1`, `Community 8`, `Community 10`, `Community 15`, `Community 20`?**
  _High betweenness centrality (0.247) - this node is a cross-community bridge._
- **Why does `sql()` connect `Community 1` to `Community 12`?**
  _High betweenness centrality (0.203) - this node is a cross-community bridge._
- **Why does `SparkSQLGenerator` connect `Community 0` to `Community 2`, `Community 3`, `Community 5`, `Community 7`, `Community 10`?**
  _High betweenness centrality (0.176) - this node is a cross-community bridge._
- **Are the 42 inferred relationships involving `SparkSQLGenerator` (e.g. with `ExplainResult` and `PySparkGenerator`) actually correct?**
  _`SparkSQLGenerator` has 42 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `ExplainResult` (e.g. with `KQLQuery` and `WhereOp`) actually correct?**
  _`ExplainResult` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `LintIssue` (e.g. with `KQLQuery` and `WhereOp`) actually correct?**
  _`LintIssue` has 12 INFERRED edges - model-reasoned connections that need verification._
- **What connects `examples/fabric_migration/01_simple_filter.py ==================================`, `The routing agent pattern from DE-Context Kit.     Routes each query to the most`, `scripts/graphify_audit.py — KQLBridge Codebase Intelligence via Graphify =======` to the rest of the system?**
  _191 weakly-connected nodes found - possible documentation gaps or missing edges._