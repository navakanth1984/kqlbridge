# ADR-01: Pipeline AST Architecture

## Context
Traditional compilers represent expression trees in deeply nested hierarchical structures. However, KQL is fundamentally a sequential pipelined query language:
```kql
T | where x | project y
```
Representing this sequentially makes transform passes and translation walks direct, logical, and highly predictable.

## Decision
The AST uses a flat list model in `KQLQuery.pipes` tracking sequential relational pipe operations, rather than a single nested AST root node. This prevents stack overflows on deep pipelines and aligns compilation passes with standard KQL conceptual stages.
