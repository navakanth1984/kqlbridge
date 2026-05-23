# ADR-03: let-Binding Query Flattening

## Context
KQL let-bindings allow data engineers to build reusable subquery variables:
```kql
let Errors = AppLogs | where Level == 'Error';
Errors | summarize count() by Service
```
Traditional compiler nesting can make the generated SQL hard to read or optimize for database engines.

## Decision
We compile all relational KQL let-bindings into standard SQL Common Table Expressions (CTEs), flattening the resulting SQL block, avoiding nested subqueries, and maximizing database execution plan optimizer efficiency.
