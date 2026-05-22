# Phase 3B Convergence Repair Guide
**KQLBridge — IRSparkSQLGenerator Category Fixes**

Run the scoreboard first, then find your category below:

```bash
py tests/convergence_report.py
# or during active repair:
py -m pytest tests/test_tier3_convergence.py::TestConvergenceReport -v -s
```

---

## How to read failure categories

The `convergence_report.json` `all_categories` field groups failures by the first
point of divergence between the oracle SQL and the IR candidate SQL. Common patterns:

```json
"all_categories": {
  "NotImpl:NotImplementedError:Unknown expr: StringOp": 41,
  "mismatch_near:like_'%value%'": 21,
  "mismatch_near:inner_join": 12,
  "Error:AttributeError":  6
}
```

---

## Category A — Formatting Drift

**Symptom:** `mismatch_near:select_*` or `length_mismatch` where both SQLs look
almost identical but differ by spacing, case, or clause ordering.

**Root cause:** The hardened `normalize_sql()` in `conftest.py` covers 12 patterns,
but an edge case isn't covered.

**Fix:** Add the new pattern to `normalize_sql()` in `conftest.py`. Example — if
`LATERAL VIEW` vs `lateral view` is failing:

```python
# In conftest.py normalize_sql():
sql = re.sub(r'\blateral\s+view\b', 'lateral view', sql)
```

**Verify:** After adding, re-run the same query in isolation:
```bash
py -m pytest tests/test_tier3_convergence.py -k "q0023" -v -s
```

---

## Category B — Expression Gaps (NotImpl)

**Symptom:** `NotImpl:NotImplementedError:Unknown expr: StringOp` or similar.

**Root cause:** A KQL expression type reaches `IRSparkSQLGenerator._emit_body()`
via a `SemanticFilter.predicate` or `ProjectionItem.expression` that is an AST
node type not handled by the inherited `_expr()` or `_bool_expr()`.

This should NOT happen for node types already in `SparkSQLGenerator` — those are
inherited automatically. It happens when the **transformer** stores something other
than the raw AST node in the IR field.

**Diagnostic — check what's in the predicate:**
```python
# Add to spark_ir.py _emit_body() temporarily:
if isinstance(step, SemanticFilter):
    print(f"DEBUG predicate type: {type(step.predicate).__name__}")
    print(f"DEBUG predicate: {step.predicate!r}")
```

**Fix A — transformer stores string instead of AST node:**
In `transformer.py`, find where `SemanticFilter` is created and confirm:
```python
# WRONG — stores rendered string:
SemanticFilter(predicate=self._bool_expr(op.condition))

# CORRECT — stores raw AST node:
SemanticFilter(predicate=op.condition)
```
The emitter calls `self._bool_expr(step.predicate)` — it needs the AST node, not
a pre-rendered string.

**Fix B — contains / has / startswith missing from _bool_expr:**
`SparkSQLGenerator._bool_expr()` already handles `StringOp`. If `IRSparkSQLGenerator`
is still failing on these, the transformer is not storing the `StringOp` AST node
correctly. Trace back to `transformer.py` `_transform_filter()`.

**Verify after fix:**
```bash
py -m pytest tests/test_emitter_convergence.py -k "contains or has or startswith" -v
```

---

## Category C — Let / CTE Chaining

**Symptom:** `mismatch_near:with_` or failures on queries containing `let` bindings.

**Root cause:** The IR's `ctes` dict is populated correctly, but `_emit_body()`
for the CTE sub-queries is not reproducing the oracle's wrapping behavior.

**Diagnostic:**
```bash
# Find a failing let query and print both SQLs:
py -m pytest tests/test_tier3_convergence.py -k "q0XXX" -v -s
# The mismatch output shows exact oracle vs candidate SQL
```

**Fix — scalar let binding handling:**
The oracle `SparkSQLGenerator.generate()` detects scalar let bindings
(`hasattr(binding.value, "scalar_expr")`) and stores them in `self._scalar_bindings`
for inline substitution rather than CTEs. Confirm `IRSparkSQLGenerator.emit()` does
the same before iterating `ir.ctes`.

Check `ir/__init__.py` — `SemanticQuery.ctes` should only contain non-scalar
bindings. Scalar bindings should be resolved into `pipeline_state` or handled
at transform time.

---

## Category D — Join ON Clause Prefix

**Symptom:** `mismatch_near:t1.key_=_t1.key` (left prefix matches right alias).

**Root cause:** The save/restore of `_current_base_table` around `_emit_body(right)`
is not working correctly. This was fixed in Phase 3A but may regress on complex
nested join patterns.

**Fix in `spark_ir.py` `_emit_join_step()`:**
```python
def _emit_join_step(self, left_table, step, existing_wheres):
    # Capture BEFORE emitting right side
    left_prefix = self._current_base_table or ...

    saved_base = self._current_base_table        # ← save
    sub_sql = self._emit_body(step.right_query)
    self._current_base_table = saved_base        # ← restore

    # Now build ON clause using left_prefix (not _current_base_table)
    on_parts = [
        f"{left_prefix}.{cond.left_col} = {right_alias}.{cond.right_col}"
        ...
    ]
```

---

## Category E — Aggregate COUNT(*) vs count()

**Symptom:** `mismatch_near:count(*)_as` or `mismatch_near:count(*)`

**Root cause:** Anonymous `count()` (no alias) produces `COUNT(*)` in the oracle
but `COUNT(*) AS None` or similar in the IR emitter.

**Fix in `spark_ir.py` `_emit_aggregate_step()`:**
The `_agg()` method (inherited) produces `COUNT(*)` with no alias when
`agg.alias is None`. The IR emitter must use `origin_node` to get exact parity:
```python
if agg_item.origin_node is not None:
    agg_cols.append(self._agg(agg_item.origin_node))
```
The `origin_node` is the raw AST `AggCount` (or `AggSum`, etc.) — using
the inherited `_agg()` on it produces bit-for-bit identical output to the oracle.

---

## Category F — UNION ALL subquery wrapping

**Symptom:** `mismatch_near:union_all` or `length_mismatch` on union queries.

**Root cause:** The oracle wraps `UNION ALL` results in `(... ) _union_result`
when further clauses follow (WHERE, GROUP BY, etc.). Check `_assemble()`:
```python
if "UNION ALL" in table and (order or limit or where_clauses or group_by or select_cols != ["*"]):
    table = "(\n" + table + "\n) _union_result"
```
The IR emitter's `_emit_union_step()` must trigger the same wrap. Confirm that
`_assemble()` (inherited from oracle) handles this automatically when passed
a `table` string containing `UNION ALL`.

---

## Repair Cycle

```
1. py tests/convergence_report.py          # see current categories
2. Pick highest-count category
3. Apply fix to spark_ir.py or transformer.py
4. py -m pytest tests/test_tier3_convergence.py -k "first_failing_id" -v -s
5. py -m pytest tests/test_emitter_convergence.py -q   # confirm no Tier1/2 regression
6. py tests/convergence_report.py          # scoreboard climbs
7. Repeat until 353/353
```

**Scoreboard should climb in steps, not one-by-one:**
Each category fix resolves a class of bugs, not a single test. A single fix to the
`origin_node` aggregate pattern should flip 15–40 tests green at once.

---

## Phase 3C flip (when 353/353)

See `translate_flip_template.py` — the exact two-line change to `__init__.py`.
