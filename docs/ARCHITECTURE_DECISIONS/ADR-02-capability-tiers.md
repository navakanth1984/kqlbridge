# ADR-02: Operator Capability Tiers

## Context
KQL operators vary significantly in their conceptual similarity to standard SQL constructs. Some translate 1:1, some require emulation, and some require structural rewrites.

## Decision
We enforce a strict 3-tier classification:
- **Tier 1 (Native):** Directly maps to standard target SQL constructs (e.g. `where`, `take`, `project`).
- **Tier 2 (Emulated):** Emulated through custom functions or multi-statement CTE logic (e.g. `extend` expressions, string Has operations).
- **Tier 3 (Synthesized):** Rewritten structurally via logical model expansion (e.g. `make-series` time grid gap fills, joins ASOF emulation).
