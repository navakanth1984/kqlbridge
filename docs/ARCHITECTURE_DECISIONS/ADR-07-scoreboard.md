# ADR-07: Scoreboard-Driven Dialect Implementation

## Context
When introducing a new database dialect target (e.g. T-SQL), prioritizing features by structural category is critical to minimize progression regressions and target effort efficiently.

## Decision
Transpiler emitter features are developed sequentially according to the real volume distribution reported by the convergence scoreboard. Primitives representing the largest share of benchmark queries (e.g., `SemanticFilter` at 32.3%) are finalized and locked first before moving to smaller buckets.
