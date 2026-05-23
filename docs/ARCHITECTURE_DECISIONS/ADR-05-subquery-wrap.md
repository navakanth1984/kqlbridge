# ADR-05: Post-Aggregate Filter Subquery Wrapping

## Context
KQL allows filtering on both physical columns and aggregated column metrics seamlessly via sequential pipes:
```kql
Logs | summarize c=count() by Service | where c > 10
```
Translating this to SQL `HAVING` causes issues in dialects like T-SQL where column aliases are not accessible in HAVING clauses.

## Decision
We utilize a unified, unconditional **Subquery Wrapping Strategy** for all post-aggregation filter operators. Instead of trying to construct complex `HAVING` segments, we wrap the aggregation step in a nested subquery and apply a standard `WHERE` filter, ensuring compatibility and alignment.
