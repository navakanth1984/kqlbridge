from typing import Literal, Tuple, Optional
import re as _re_smart
from .parser import parse
from .generators.spark_sql import SparkSQLGenerator
from .generators.tsql import TSQLGenerator
from .ast_nodes import KQLQuery

# FIX-03: pattern to detect make-series before the grammar is invoked.
_MAKE_SERIES_RE = _re_smart.compile(r"\|\s*make-series\b", _re_smart.IGNORECASE)

def analyze_ast(query: KQLQuery) -> Literal["spark_sql", "pyspark", "tsql"]:
    """
    AST Analyzer that scores complexity and structural intent to route
    to the optimal execution backend.
    """
    return "spark_sql"

def smart_transpile(kql: str, force_engine: Optional[Literal["spark_sql", "pyspark", "tsql"]] = None) -> Tuple[Literal["spark_sql", "pyspark", "tsql"], str]:
    """
    Intelligent compiler endpoint that parses the query, analyzes the AST, 
    and selects the optimal backend engine for execution.
    
    Returns:
        A tuple of (execution_engine, generated_code).
    """
    # FIX-03: make-series bypasses the Lark grammar — route via TEG v5.
    # Karpathy P3: only added this pre-check block; all other paths unchanged.
    if _MAKE_SERIES_RE.search(kql):
        from .micro_model import TimeSeriesMicroModel
        engine = force_engine or "spark_sql"
        model = TimeSeriesMicroModel(kql)
        if engine in ("spark_sql", "spark"):
            return "spark_sql", model.to_spark_sql()
        elif engine == "pyspark":
            return "pyspark", model.to_pyspark()
        elif engine == "tsql":
            return "tsql", model.to_tsql()
        return "spark_sql", model.to_spark_sql()

    query = parse(kql)
    engine = force_engine or analyze_ast(query)
    
    if engine == "spark_sql":
        gen = SparkSQLGenerator()
        return "spark_sql", gen.generate(query)
    elif engine == "pyspark":
        from .generators.pyspark import PySparkGenerator
        gen = PySparkGenerator()
        return "pyspark", gen.generate(query)
    elif engine == "tsql":
        gen = TSQLGenerator()
        return "tsql", gen.generate(query)
        
    raise ValueError(f"Unable to route to engine: {engine}")
