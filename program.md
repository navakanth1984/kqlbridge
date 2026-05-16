# program.md — KQLBridge Build Contract

> This file defines the agent's goal, rules, and constraints.
> The agent reads this. The agent **NEVER** modifies this file.
> Human reviews this file before every BIT Build session.

---

## Goal

Implement KQL operators in `src/kqlbridge/parser.py` and `src/kqlbridge/generators/spark_sql.py`
such that the locked eval harness (`tests/eval/prepare.py`) returns a score ≥ **85%** on the
full 100-query benchmark.

**Scalar metric (the only thing that counts):**
```
prepare.py → SCORE: {pct:.1f}% ({pass}/{total})
```

Target: ≥ 85.0% (85 / 100 cases passing).

---

## Files You MAY Modify

```
src/kqlbridge/parser.py
src/kqlbridge/generators/spark_sql.py
src/kqlbridge/generators/tsql.py       (v0.2 only — do not touch in v0.1 sessions)
src/kqlbridge/generators/kql_reverse.py (v0.2 only — do not touch in v0.1 sessions)
```

---

## Files You MUST NEVER Modify

```
tests/eval/prepare.py       # 🔒 LOCKED oracle — the eval script
tests/eval/benchmark.json   # 🔒 LOCKED test cases — 100 queries
src/kqlbridge/ast_nodes.py  # 🔒 LOCKED AST type definitions
src/kqlbridge/grammar/kql.lark  # 🔒 LOCKED grammar
src/kqlbridge/semantic.py   # 🔒 LOCKED semantic validator
pyproject.toml              # 👤 HUMAN ONLY
docs/                       # 👤 HUMAN ONLY
LICENSE                     # 👤 HUMAN ONLY
README.md                   # 👤 HUMAN ONLY
program.md                  # 👤 THIS FILE — NEVER TOUCH
```

---

## Rules

1. **Every change must be traceable to a failing benchmark case.**
   Reference the case ID (e.g., `std_001`) in your commit message.

2. **Do not add features beyond the failing case.**
   If `std_001` needs `where`, implement `where` only. Do not pre-implement `extend`.

3. **Do not refactor adjacent working code.**
   If `_where()` is passing all its cases, do not touch it while fixing `_summarize()`.
   If you notice a problem in passing code — mention it. Do not fix it.

4. **If unsure: stop and surface the ambiguity. Do not guess.**
   Especially for `summarize` → `GROUP BY` rewrites, which are the most likely source
   of silent semantic failures. Ask the human to verify the mapping before implementing.

5. **After each change: state what you changed and why.**
   Format: `[case std_NNN] implemented _summarize() aggregate rewrite — score: X → Y%`

6. **Time budget: 30 seconds per test case.**
   The oracle enforces this. Do not write logic that relies on slow iteration.

7. **Karpathy Principle 2 — Simplicity First.**
   One method per operator. No abstractions until the same pattern appears in ≥ 3 operators.
   If you've written 50 lines for one operator — rewrite it shorter.

---

## Success Criterion (Scalar)

```
tests/eval/prepare.py returns SCORE ≥ 85.0%
```

No other criterion counts. A score of 84.9% is a failure.
A score of 85.0% is v0.1 shipped.

---

## BIT Loop Cadence

| Phase | When | What you do |
|---|---|---|
| **Build** | Each operator | Modify parser.py or spark_sql.py — one operator at a time |
| **Integrate** | After each operator is green | Update `operator_status.md`. Human confirms before session closes. |
| **Tune** | Every 3–5 operators | Run bloat audit checklist. Propose refactors. Human approves. |

---

## Bloat Audit Checklist (run after every successful Build)

```
□ Can any 10+ line block become a named function?
□ Are there copy-pasted patterns → should be a loop?
□ Are there abstractions for only one operator?
□ Are there unreachable branches?
□ Does the code optimize for the score but miss real cases?
□ Would a senior engineer understand this in 5 minutes?
```

If any answer is YES (or NO for the last one) — refactor before closing the session.

---

## AutoResearch Mapping

```
program.md       → This file (goals, rules, constraints) — LOCKED
train.py         → parser.py + generators/spark_sql.py  — MODIFIABLE
prepare.py       → tests/eval/prepare.py                — LOCKED ORACLE
```

The agent cannot rewrite the rules of success. The oracle is fixed.
