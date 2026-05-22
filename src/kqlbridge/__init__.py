"""
kqlbridge — KQL to Spark SQL / T-SQL transpiler
================================================
Public API:

    translate(kql, target="spark") → str
    detect_operators(kql) → list[str]
    is_supported(kql) → bool
    check(kql) → SemanticResult
"""

from __future__ import annotations
from typing import Literal
from enum import Enum

from .parser import parse
from lark.exceptions import UnexpectedInput as _LarkUnexpectedInput
from .semantic import check as _semantic_check, SemanticResult
from .lint import lint, LintResult  # noqa: F401 — public API
from .explain import explain, ExplainResult  # noqa: F401 — public API
from .generators.spark_sql import SparkSQLGenerator
from .generators.tsql import TSQLGenerator
from .generators.pyspark import PySparkGenerator

from .smart import smart_transpile, smart_analyze
from .micro_model import TimeSeriesMicroModel
from .schema_hint import SchemaHint, WindowSpec

from .memory import TranslationMemory
from .registry import (
    CapabilityLevel, SUPPORT_MATRIX, get_capability_level,
    is_operator_supported, get_supported_dialects
)
from .plugins import (
    register_renderer, register_optimizer, register_operator, register_function
)
from .optimizer import ASTOptimizer, OptimizationRule

# FIX-05: declare output type contract — Pandas/PySpark return Python code,
# not SQL strings. Callers must branch on OutputType before passing to an engine.
class OutputType(Enum):
    SQL = "sql"       # Spark SQL, T-SQL — run through a SQL engine
    PYTHON = "python" # Pandas, PySpark — execute as Python code

def target_output_type(target: str) -> OutputType:
    """Return the OutputType for a given translate() target string."""
    return OutputType.PYTHON if target in ("pandas", "pyspark") else OutputType.SQL

__version__ = "0.11.4"  # patched: FIX-01 through FIX-05 and True Bool Suffix Bug + ruff fixes
__all__ = [
    "translate", "smart_transpile", "smart_analyze", "detect_operators", "is_supported",
    "check", "__version__", "TimeSeriesMicroModel",
    "OutputType", "target_output_type",  # FIX-05
    "SchemaHint", "WindowSpec",
    "TranslationMemory", "translation_memory",
    "MLMAgent", "mlm_agent",
    "CapabilityLevel", "SUPPORT_MATRIX", "get_capability_level",
    "is_operator_supported", "get_supported_dialects",
    "register_renderer", "register_optimizer", "register_operator", "register_function",
    "ASTOptimizer", "OptimizationRule",
]

# Thread-safe global instance of TranslationMemory
translation_memory = TranslationMemory()
mlm_agent = translation_memory
MLMAgent = TranslationMemory



def normalize_hint(hint: SchemaHint | dict | None) -> SchemaHint | None:
    if hint is None:
        return None
    if isinstance(hint, SchemaHint):
        return hint
    if isinstance(hint, dict):
        ws_val = hint.get("window_spec")
        ws = None
        if isinstance(ws_val, dict):
            ws = WindowSpec(
                partition_by=ws_val.get("partition_by"),
                order_by=ws_val.get("order_by")
            )
        elif isinstance(ws_val, WindowSpec):
            ws = ws_val
        
        return SchemaHint(
            window_spec=ws,
            json_fields=hint.get("json_fields"),
            target_dialect=hint.get("target_dialect")
        )
    return None


def translate(
    kql: str,
    target: Literal["spark", "tsql", "pyspark"] = "spark",
    hint: SchemaHint | dict | None = None,
) -> str:
    """
    Translate a KQL query string to the target SQL dialect.

    Args:
        kql:    KQL query string
        target: "spark" (default), "tsql", or "pyspark"
        hint:   Optional SchemaHint context to configure window/schema specs

    Returns:
        SQL/Python string in the target dialect

    Raises:
        lark.exceptions.UnexpectedInput: on KQL parse error
        NotImplementedError: if target generator is not implemented
        ValueError: if query contains unsupported operators (check first)
    """
    hint = normalize_hint(hint)

    # 1. Translation Memory pre-execution recall hook
    override_sql = translation_memory.recall(kql)
    if override_sql is not None:
        translation_memory.learn(kql)
        return override_sql

    try:
        normalized_kql = " ".join(kql.lower().split())

        if "make-series" in normalized_kql:
            from .micro_model import TimeSeriesMicroModel
            model = TimeSeriesMicroModel(kql)
            if target == "spark":
                res = model.to_spark_sql()
            elif target == "tsql":
                res = model.to_tsql()
            elif target == "pyspark":
                res = model.to_pyspark()
            else:
                raise ValueError(f"Unknown target: {target!r}. Use 'spark', 'tsql', or 'pyspark'.")
            translation_memory.learn(kql)
            return res

        try:
            query = parse(kql)
            from .scoping import ScopeManager
            from .passes.alpha_renaming import AlphaRenamer
            from .passes.constant_folding import ConstantFolder
            
            scope_manager = ScopeManager()
            query = AlphaRenamer(scope_manager).rename_query(query)
            query = ConstantFolder(scope_manager).fold_query(query)
            
            from .optimizer import ASTOptimizer
            query = ASTOptimizer().optimize(query)
            
            # Dry-run Semantic IR validation pass
            try:
                from .ir import to_semantic_ir, validate_ir
                ir_query = to_semantic_ir(query, scope_manager.current_scope)
                validate_ir(ir_query)
            except Exception as ir_err:
                raise ValueError(f"Dry-run Semantic IR validation failed: {ir_err}") from ir_err
        except _LarkUnexpectedInput as e:
            raise ValueError(
                "Unsupported KQL syntax — contains operators or constructs not supported "
                "in this version. Use is_supported() to check before translating.\n"
                f"Detail: {e}"
            ) from None

        if target == "spark":
            from .ir.emitters.spark_ir import IRSparkSQLGenerator
            res = IRSparkSQLGenerator(hint=hint).emit(ir_query)
        elif target == "tsql":
            res = TSQLGenerator(hint=hint).generate(query)
        elif target == "pyspark":
            res = PySparkGenerator(hint=hint).generate(query)
        else:
            raise ValueError(f"Unknown target: {target!r}. Use 'spark', 'tsql', or 'pyspark'.")

        translation_memory.learn(kql)
        return res

    except Exception as e:
        translation_memory.learn(kql, error=str(e))
        raise


def detect_operators(kql: str) -> list[str]:
    """
    Return the list of KQL operators used in a query string.

    Useful for routing agents that need to decide which engine to use.

    Example:
        detect_operators("T | where x == 1 | summarize count() by y")
        → ['where', 'summarize']
    """
    from .ast_nodes import (
        WhereOp, ProjectOp, SummarizeOp, OrderOp, TakeOp,
        DistinctOp, ExtendOp, JoinOp, UnionOp, CountOp,
    )
    _OP_NAMES = {
        WhereOp: "where",
        ProjectOp: "project",
        SummarizeOp: "summarize",
        OrderOp: "order by",
        TakeOp: "take",
        DistinctOp: "distinct",
        ExtendOp: "extend",
        JoinOp: "join",
        UnionOp: "union",
        CountOp: "count",
    }

    # FIX-03: detect make-series and fill functions BEFORE calling the grammar
    # parser, which doesn't have a make-series production rule yet.
    # Karpathy P3: only added this pre-check block; _OP_NAMES dict unchanged.
    import re as _re_detect
    ops: list[str] = []
    normalized = " ".join(kql.lower().split())
    if _re_detect.search(r"\|\s*make-series\b", normalized):
        ops.append("make-series")
    if _re_detect.search(r"\bseries_fill_linear\s*\(", normalized):
        ops.append("series_fill_linear")
    if _re_detect.search(r"\bseries_fill_forward\s*\(", normalized):
        ops.append("series_fill_forward")

    # For mixed pipelines (e.g. "T | where x | make-series ..."), truncate at
    # the make-series pipe so the grammar can still detect preceding operators.
    kql_for_grammar = _re_detect.split(r"\|\s*make-series\b", kql, maxsplit=1, flags=_re_detect.IGNORECASE)[0].rstrip(" |")

    try:
        query = parse(kql_for_grammar)
        ops += [_OP_NAMES[type(op)] for op in query.pipes
                if type(op) in _OP_NAMES]
    except Exception:
        pass  # grammar failed — ops from pre-check still returned
    return ops


def is_supported(kql: str) -> bool:
    """
    Return True if the query can be fully translated to Spark SQL.

    Queries with unsupported operators (make-series, render, etc.)
    return False — the caller should keep those in the native KQL engine.
    """
    # FIX-03: make-series is handled via TEG v5 (TimeSeriesMicroModel).
    # The Lark grammar doesn't have a make-series rule yet, so parse() raises.
    # We pre-check for it and return True since translate() handles it.
    import re as _re_sup
    normalized = " ".join(kql.lower().split())
    if _re_sup.search(r"\|\s*make-series\b", normalized):
        return True  # TEG v5 handles this path

    try:
        query = parse(kql)
        result = _semantic_check(query)
        return result.is_supported
    except Exception:
        return False


def check(kql: str) -> SemanticResult:
    """
    Parse and semantically validate a KQL query.

    Returns a SemanticResult with:
    - is_valid: True if AST is structurally sound
    - is_supported: True if query can be fully translated
    - warnings: Non-blocking issues
    - errors: Blocking issues (unsupported operators, ambiguities)
    """
    # FIX-03: make-series bypasses the Lark grammar via TEG v5.
    # Return a valid SemanticResult without calling parse() on it.
    import re as _re_chk
    normalized = " ".join(kql.lower().split())
    if _re_chk.search(r"\|\s*make-series\b", normalized):
        return SemanticResult(
            is_valid=True,
            warnings=["make-series handled via TEG v5 (TimeSeriesMicroModel)"],
            errors=[],
        )
    query = parse(kql)
    return _semantic_check(query)
