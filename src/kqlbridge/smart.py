from typing import Literal, Tuple, Optional
from .parser import parse
from .generators.spark_sql import SparkSQLGenerator
from .generators.tsql import TSQLGenerator
from .ast_nodes import KQLQuery

def analyze_ast(query: KQLQuery) -> Literal["spark_sql", "pyspark", "tsql"]:
    """
    AST Analyzer that scores complexity and structural intent to route
    to the optimal execution backend.
    """
    # In the future, this will scan for:
    # 1. Custom UDFs / ML plugins -> route to pyspark
    # 2. Complex recursive let bindings -> route to pyspark
    # 3. Time series forecasting (make-series) -> route to pyspark
    
    # For now, KQLBridge only parses pure relational operations,
    # so we confidently route to the optimized Spark SQL Catalyst engine.
    return "spark_sql"

def smart_transpile(kql: str, force_engine: Optional[Literal["spark_sql", "pyspark", "tsql"]] = None) -> Tuple[Literal["spark_sql", "pyspark", "tsql"], str]:
    """
    Intelligent compiler endpoint that parses the query, analyzes the AST, 
    and selects the optimal backend engine for execution.
    
    Returns:
        A tuple of (execution_engine, generated_code).
    """
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
