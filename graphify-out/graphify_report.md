# Graph Report - kqlbridge  (2026-05-19)

## Corpus Check
- Corpus is ~9,548 words - fits in a single context window. You may not need a graph.

## Summary
- 226 nodes · 489 edges · 10 communities (9 shown, 1 thin omitted)
- Extraction: 75% EXTRACTED · 25% INFERRED · 0% AMBIGUOUS · INFERRED: 120 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

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

## God Nodes (most connected - your core abstractions)
1. `SparkSQLGenerator` - 60 edges
2. `PySparkGenerator` - 24 edges
3. `ExplainResult` - 23 edges
4. `_build_expr()` - 20 edges
5. `LintIssue` - 19 edges
6. `TSQLGenerator` - 16 edges
7. `_build_bool_expr()` - 15 edges
8. `LintResult` - 14 edges
9. `KQLQuery` - 12 edges
10. `parse()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `LintIssue` --uses--> `ColumnRef`  [INFERRED]
  lint.py → ast_nodes.py
- `LintResult` --uses--> `ColumnRef`  [INFERRED]
  lint.py → ast_nodes.py
- `SemanticResult` --uses--> `ColumnRef`  [INFERRED]
  semantic.py → ast_nodes.py
- `SparkSQLGenerator` --uses--> `ColumnRef`  [INFERRED]
  generators/spark_sql.py → ast_nodes.py
- `TSQLGenerator` --uses--> `ColumnRef`  [INFERRED]
  generators/tsql.py → ast_nodes.py

## Communities (10 total, 1 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.08
Nodes (42): AggAvg, AggCount, AggCountIf, AggDCount, AggMax, AggMin, AggSum, BinaryOp (+34 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (27): generators/spark_sql.py — KQL AST → Spark SQL ==================================, # NOTE: do NOT clear where_clauses — WHERE filters from before, generators/tsql.py — KQL AST → T-SQL ===================================== AGENT, _check(), _lint(), cli.py — KQLBridge command-line interface ======================================, _translate(), check() (+19 more)

### Community 2 - "Community 2"
Cohesion: 0.1
Nodes (28): PySparkGenerator, Main entry point for PySpark generation., Experimental PySpark Generator.     Routes KQL AST nodes to executable PySpark D, BinGroup, Comparison, DistinctOp, ExtendOp, LogicalOp (+20 more)

### Community 3 - "Community 3"
Cohesion: 0.13
Nodes (13): Returns (select_cols, group_by_cols).          Karpathy P5 — Jagged Intelligence, Render a single aggregation expression., KQL join → SQL INNER/LEFT/RIGHT/FULL JOIN.         Returns a 'table expression', KQL union T1, T2 or union (T1 | ...) → UNION ALL, Render bin(col, N<unit>) → Spark SQL timestamp bucketing.         - Hourly or co, Render a scalar expression to SQL., Map KQL built-in functions to Spark SQL equivalents.         Only functions need, Render a boolean expression to a SQL WHERE fragment. (+5 more)

### Community 4 - "Community 4"
Cohesion: 0.13
Nodes (25): CountOp, JoinOp, KQLQuery, PlainGroup, | join kind=inner (RightTable | ...) on key, | union T2, T3  or  | union (T2 | where ...), T3, The root AST node. Represents a complete KQL query.      let_bindings → will bec, TakeOp (+17 more)

### Community 5 - "Community 5"
Cohesion: 0.12
Nodes (15): lint.py — KQLBridge Semantic Drift Detector ====================================, LINT-03: bin(ts, 7d) buckets from Unix epoch, not calendar weeks., LINT-04: let bindings that reference earlier bindings may not resolve., LINT-05: extend col = col — self-assignment is ambiguous in Spark SQL., LINT-06: distinct * after project returns same rows as project alone., LINT-01: =~ operator is case-insensitive in KQL, becomes = in SQL., LINT-02: has is word-boundary aware in KQL, LIKE '%x%' is not., _rule_lint01_case_insensitive_op() (+7 more)

### Community 6 - "Community 6"
Cohesion: 0.2
Nodes (13): _explain(), _annotate_bin(), _annotate_op(), _annotate_query(), _annotate_where(), _build_annotated_sql(), explain(), _expr_note() (+5 more)

### Community 7 - "Community 7"
Cohesion: 0.18
Nodes (9): Generates T-SQL from a KQLQuery AST.     Inherits from SparkSQLGenerator — overr, TSQLGenerator, AgoExpr, BinExpr, DatetimeLit, A KQL datetime literal: datetime(2024-01-01), KQL ago(1h) → CURRENT_TIMESTAMP - INTERVAL '1 hours, KQL bin(col, 1h) → DATE_TRUNC('hour', col) (+1 more)

### Community 8 - "Community 8"
Cohesion: 0.25
Nodes (9): check(), _check_let_bindings(), _check_pipes(), _check_summarize_rewrite(), semantic.py — KQLBridge Semantic Validator =====================================, Let bindings become CTEs. Circular references are not supported., Run semantic validation on a parsed KQLQuery.      Returns a SemanticResult with, Karpathy Principle 5 — Jagged Intelligence warning site.      KQL summarize is l (+1 more)

## Knowledge Gaps
- **78 isolated node(s):** `ast_nodes.py — KQLBridge Typed AST Node Definitions ============================`, `A reference to a column: e.g. ServiceName`, `A string literal: 'Error' or "Error"`, `An integer literal: 100`, `A float literal: 3.14` (+73 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SparkSQLGenerator` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 4`, `Community 7`?**
  _High betweenness centrality (0.318) - this node is a cross-community bridge._
- **Why does `TSQLGenerator` connect `Community 7` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 6`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Why does `PySparkGenerator` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Are the 42 inferred relationships involving `SparkSQLGenerator` (e.g. with `ExplainResult` and `PySparkGenerator`) actually correct?**
  _`SparkSQLGenerator` has 42 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `PySparkGenerator` (e.g. with `KQLQuery` and `ProjectOp`) actually correct?**
  _`PySparkGenerator` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `ExplainResult` (e.g. with `KQLQuery` and `WhereOp`) actually correct?**
  _`ExplainResult` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `LintIssue` (e.g. with `KQLQuery` and `WhereOp`) actually correct?**
  _`LintIssue` has 12 INFERRED edges - model-reasoned connections that need verification._