from __future__ import annotations
from typing import Literal, Tuple, Optional, Dict, Any
import re as _re_smart
from .parser import parse
from .generators.spark_sql import SparkSQLGenerator
from .generators.tsql import TSQLGenerator
from .ast_nodes import KQLQuery

# Pattern to detect make-series before the grammar is invoked.
_MAKE_SERIES_RE = _re_smart.compile(r"\|\s*make-series\b", _re_smart.IGNORECASE)

def smart_analyze(kql: str) -> Dict[str, Any]:
    """
    Compiler-grade query strategy analyzer.
    Analyzes the KQL input text to recommend execution strategies,
    complexity scores, and target engine recommendations without mutating/overriding
    user translation intents.
    
    Returns a dictionary:
        {
            "strategy": "timeseries" | "dataframe" | "sql",
            "complexity": int (1 to 10 scale),
            "recommended_engine": "spark" | "tsql" | "pyspark"
        }
    """
    normalized = " ".join(kql.lower().split())
    
    # 1. Strategy Identification
    if _MAKE_SERIES_RE.search(normalized):
        strategy = "timeseries"
        recommended_engine = "spark"
    elif "union" in normalized or "join" in normalized:
        strategy = "sql"
        recommended_engine = "spark"
    elif "extend" in normalized and len(normalized.split("|")) > 3:
        strategy = "dataframe"
        recommended_engine = "pyspark"
    else:
        strategy = "sql"
        recommended_engine = "spark"
        
    # 2. Complexity Calculation
    complexity = 1
    # Count pipeline stages
    pipe_count = len(kql.split("|")) - 1
    complexity += pipe_count
    
    # Boost complexity for joins, unions and nested operations
    if "join" in normalized:
        complexity += 3
    if "union" in normalized:
        complexity += 2
    if "make-series" in normalized:
        complexity += 4
    if "iff(" in normalized or "case(" in normalized:
        complexity += 2
        
    complexity = min(10, complexity)
    
    return {
        "strategy": strategy,
        "complexity": complexity,
        "recommended_engine": recommended_engine
    }

def analyze_ast(query: KQLQuery) -> Literal["spark_sql", "pyspark", "tsql"]:
    """
    Backward-compatibility AST Analyzer mapping KQLQuery to target engine string.
    """
    # Simple heuristic
    has_join = any(getattr(op, "__class__", None).__name__ == "JoinOp" for op in query.pipes)
    if has_join:
        return "spark_sql"
    return "spark_sql"

def smart_transpile(
    kql: str, 
    force_engine: Optional[Literal["spark_sql", "pyspark", "tsql"]] = None
) -> Tuple[Literal["spark_sql", "pyspark", "tsql"], str]:
    """
    Intelligent compiler endpoint that analyzes strategy, runs translation,
    and returns a tuple of (execution_engine, generated_code).
    """
    analysis = smart_analyze(kql)
    engine = force_engine or analysis["recommended_engine"]
    
    # Normalize engine name to match backward-compatible output strings
    if engine == "spark":
        engine = "spark_sql"
        
    if _MAKE_SERIES_RE.search(kql):
        from .micro_model import TimeSeriesMicroModel
        model = TimeSeriesMicroModel(kql)
        if engine in ("spark_sql", "spark"):
            return "spark_sql", model.to_spark_sql()
        elif engine == "pyspark":
            return "pyspark", model.to_pyspark()
        elif engine == "tsql":
            return "tsql", model.to_tsql()
        return "spark_sql", model.to_spark_sql()

    query = parse(kql)
    # Apply optimizations inside the translate layer, which parses internally.
    # For smart_transpile, optimization is handled transparently.
    from .optimizer import ASTOptimizer
    optimized_query = ASTOptimizer().optimize(query)
    
    if engine == "spark_sql":
        gen = SparkSQLGenerator()
        return "spark_sql", gen.generate(optimized_query)
    elif engine == "pyspark":
        from .generators.pyspark import PySparkGenerator
        gen = PySparkGenerator()
        return "pyspark", gen.generate(optimized_query)
    elif engine == "tsql":
        gen = TSQLGenerator()
        return "tsql", gen.generate(optimized_query)
        
    raise ValueError(f"Unable to route to engine: {engine}")
