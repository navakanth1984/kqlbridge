"""
translate_flip_template.py — Phase 3C: The translate() Switch
=============================================================
APPLY ONLY WHEN: test_phase3b_gate.py::TestPhase3BGate::test_phase3b_complete_gate PASSES

This file documents the exact two changes required to flip translate()
from the legacy AST path to the IR-driven path.

DO NOT apply until convergence_report.json shows:
    "phase3b_complete": true

Gate check:
    py -m pytest tests/test_phase3b_gate.py -v
"""

# ═══════════════════════════════════════════════════════════════════════════════
# CHANGE 1 of 2 — src/kqlbridge/__init__.py  (or wherever translate() lives)
#
# Find the translate() function and add the `use_ir` parameter.
# The existing AST path stays intact as the fallback.
# ═══════════════════════════════════════════════════════════════════════════════

TRANSLATE_CHANGE = '''
# BEFORE (existing):
def translate(kql: str, target: str = "spark", hint=None) -> str:
    query = parse(kql)
    if target == "spark":
        return SparkSQLGenerator(hint).generate(query)
    elif target == "tsql":
        return TSQLGenerator(hint).generate(query)
    elif target == "pyspark":
        return PySparkGenerator(hint).generate(query)
    raise ValueError(f"Unknown target: {target!r}")


# AFTER (Phase 3C — IR path becomes authoritative):
def translate(
    kql: str,
    target: str = "spark",
    hint=None,
    use_ir: bool = True,          # ← flip default to True when gate passes
) -> str:
    """
    Translate a KQL query string to the target SQL dialect.

    Args:
        kql:    KQL query string.
        target: Output dialect — "spark" | "tsql" | "pyspark".
        hint:   Optional SchemaHint for type-aware rendering.
        use_ir: When True (default after Phase 3C), routes through the
                Semantic IR layer with validation. Set False to use the
                legacy AST path (kept for regression debugging).
    """
    query = parse(kql)

    if use_ir:
        from .ir import to_semantic_ir
        ir = to_semantic_ir(query, validate=True)

        if target == "spark":
            from .ir.emitters.spark_ir import IRSparkSQLGenerator
            return IRSparkSQLGenerator(hint).emit(ir)

        # TSQL and PySpark IR emitters added in Phase 3C:
        if target == "tsql":
            from .ir.emitters.tsql_ir import IRTSQLGenerator
            return IRTSQLGenerator(hint).emit(ir)

        if target == "pyspark":
            from .ir.emitters.pyspark_ir import IRPySparkGenerator
            return IRPySparkGenerator(hint).emit(ir)

    # Legacy AST path — retained for fallback and debugging
    if target == "spark":
        return SparkSQLGenerator(hint).generate(query)
    elif target == "tsql":
        return TSQLGenerator(hint).generate(query)
    elif target == "pyspark":
        return PySparkGenerator(hint).generate(query)

    raise ValueError(f"Unknown target: {target!r}")
'''

# ═══════════════════════════════════════════════════════════════════════════════
# CHANGE 2 of 2 — The retirement marker for legacy generators
#
# Add this docstring to SparkSQLGenerator, TSQLGenerator, PySparkGenerator
# so contributors know the deprecation intent.
# ═══════════════════════════════════════════════════════════════════════════════

LEGACY_DEPRECATION_MARKER = '''
class SparkSQLGenerator:
    """
    Legacy AST-driven Spark SQL emitter.

    Status: RETAINED for regression debugging and fallback.
    Authoritative path: IRSparkSQLGenerator (Phase 3C+).

    Do not add new features here — implement in ir/emitters/spark_ir.py.
    Scheduled for removal in v2.0 after 353/353 convergence is proven stable.
    """
'''

# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICATION SEQUENCE (run after applying)
# ═══════════════════════════════════════════════════════════════════════════════

VERIFICATION = """
After applying the translate() flip:

1. Smoke test — confirm IR path works:
   py -c "from kqlbridge import translate; print(translate('T | where x == 1'))"

2. Full suite with IR path:
   py -m pytest -q
   Expected: same pass count as before the flip

3. Confirm legacy fallback still works:
   py -c "from kqlbridge import translate; print(translate('T | where x == 1', use_ir=False))"

4. Run the gate:
   py -m pytest tests/test_phase3b_gate.py -v

5. Update convergence history:
   py tests/convergence_report.py
"""

if __name__ == "__main__":
    print("translate() flip template — see TRANSLATE_CHANGE and LEGACY_DEPRECATION_MARKER")
    print("Apply ONLY after test_phase3b_gate.py passes.")
    print(VERIFICATION)
