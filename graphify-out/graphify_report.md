# Graph Report - kqlbridge  (2026-05-20)

## Corpus Check
- Corpus is ~12,216 words - fits in a single context window. You may not need a graph.

## Summary
- 257 nodes · 577 edges · 11 communities (10 shown, 1 thin omitted)
- Extraction: 76% EXTRACTED · 24% INFERRED · 0% AMBIGUOUS · INFERRED: 140 edges (avg confidence: 0.52)
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
- [[_COMMUNITY_Community 10|Community 10]]

## God Nodes (most connected - your core abstractions)
1. `SparkSQLGenerator` - 74 edges
2. `TSQLGenerator` - 29 edges
3. `PySparkGenerator` - 26 edges
4. `ExplainResult` - 23 edges
5. `_build_expr()` - 21 edges
6. `LintIssue` - 19 edges
7. `_build_agg_func()` - 19 edges
8. `_build_bool_expr()` - 17 edges
9. `parse()` - 16 edges
10. `LintResult` - 14 edges

## Surprising Connections (you probably didn't know these)
- `_explain()` --calls--> `explain()`  [INFERRED]
  cli.py → explain.py
- `LintIssue` --uses--> `ColumnRef`  [INFERRED]
  lint.py → ast_nodes.py
- `LintResult` --uses--> `ColumnRef`  [INFERRED]
  lint.py → ast_nodes.py
- `SemanticResult` --uses--> `ColumnRef`  [INFERRED]
  semantic.py → ast_nodes.py
- `SparkSQLGenerator` --uses--> `ColumnRef`  [INFERRED]
  generators/spark_sql.py → ast_nodes.py

## Communities (11 total, 1 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.11
Nodes (30): PySparkGenerator, Main entry point for PySpark generation., Experimental PySpark Generator.     Routes KQL AST nodes to executable PySpark D, BinGroup, Comparison, CountOp, DistinctOp, LogicalOp (+22 more)

### Community 1 - "Community 1"
Cohesion: 0.11
Nodes (13): Walk the pipe operators and accumulate SQL clause fragments.         The assembl, Returns (select_cols, group_by_cols).          Karpathy P5 — Jagged Intelligence, Render a single aggregation expression., KQL join → SQL INNER/LEFT/RIGHT/FULL JOIN.         Returns a 'table expression', KQL union T1, T2 or union (T1 | ...) → UNION ALL, Render bin(col, N<unit>) → Spark SQL timestamp bucketing.         - Hourly or co, Render a scalar expression to SQL., Map KQL built-in functions to Spark SQL equivalents.         Only functions need (+5 more)

### Community 2 - "Community 2"
Cohesion: 0.1
Nodes (33): ExtendOp, KQLQuery, | extend alias = expr, The root AST node. Represents a complete KQL query.      let_bindings → will bec, _build_agg_item(), _build_agg_list(), _build_distinct(), _build_extend() (+25 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (23): generators/spark_sql.py — KQL AST → Spark SQL ==================================, # NOTE: do NOT clear where_clauses — WHERE filters from before, generators/tsql.py — KQL AST → T-SQL ===================================== AGENT, _check(), _explain(), _lint(), cli.py — KQLBridge command-line interface ======================================, _translate() (+15 more)

### Community 4 - "Community 4"
Cohesion: 0.09
Nodes (31): AggAvg, AggAvgIf, AggCount, AggCountIf, AggDCount, AggDCountIf, AggMakeList, AggMax (+23 more)

### Community 5 - "Community 5"
Cohesion: 0.13
Nodes (23): BinaryOp, BoolLit, ColumnRef, FloatLit, IffExpr, InExpr, IntLit, NullCheck (+15 more)

### Community 6 - "Community 6"
Cohesion: 0.15
Nodes (11): Generates T-SQL from a KQLQuery AST.     Inherits from SparkSQLGenerator — overr, TSQLGenerator, AgoExpr, BinExpr, DatetimeLit, HasAnyExpr, col has_any ('val1', 'val2'), A KQL datetime literal: datetime(2024-01-01) (+3 more)

### Community 7 - "Community 7"
Cohesion: 0.12
Nodes (15): lint.py — KQLBridge Semantic Drift Detector ====================================, LINT-03: bin(ts, 7d) buckets from Unix epoch, not calendar weeks., LINT-04: let bindings that reference earlier bindings may not resolve., LINT-05: extend col = col — self-assignment is ambiguous in Spark SQL., LINT-06: distinct * after project returns same rows as project alone., LINT-01: =~ operator is case-insensitive in KQL, becomes = in SQL., LINT-02: has is word-boundary aware in KQL, LIKE '%x%' is not., _rule_lint01_case_insensitive_op() (+7 more)

### Community 8 - "Community 8"
Cohesion: 0.22
Nodes (12): _annotate_bin(), _annotate_op(), _annotate_query(), _annotate_where(), _build_annotated_sql(), explain(), _expr_note(), explain.py — KQLBridge Translation Annotator =================================== (+4 more)

### Community 9 - "Community 9"
Cohesion: 0.19
Nodes (12): JoinOp, PlainGroup, | join kind=inner (RightTable | ...) on key, check(), _check_let_bindings(), _check_pipes(), _check_summarize_rewrite(), semantic.py — KQLBridge Semantic Validator ===================================== (+4 more)

## Knowledge Gaps
- **85 isolated node(s):** `ast_nodes.py — KQLBridge Typed AST Node Definitions ============================`, `A reference to a column: e.g. ServiceName`, `A string literal: 'Error' or "Error"`, `An integer literal: 100`, `A float literal: 3.14` (+80 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SparkSQLGenerator` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 9`?**
  _High betweenness centrality (0.330) - this node is a cross-community bridge._
- **Why does `TSQLGenerator` connect `Community 6` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 8`?**
  _High betweenness centrality (0.107) - this node is a cross-community bridge._
- **Why does `PySparkGenerator` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 9`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Are the 51 inferred relationships involving `SparkSQLGenerator` (e.g. with `ExplainResult` and `PySparkGenerator`) actually correct?**
  _`SparkSQLGenerator` has 51 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `TSQLGenerator` (e.g. with `ExplainResult` and `AgoExpr`) actually correct?**
  _`TSQLGenerator` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `PySparkGenerator` (e.g. with `KQLQuery` and `ProjectOp`) actually correct?**
  _`PySparkGenerator` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `ExplainResult` (e.g. with `KQLQuery` and `WhereOp`) actually correct?**
  _`ExplainResult` has 21 INFERRED edges - model-reasoned connections that need verification._