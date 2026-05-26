from __future__ import annotations
from kqlbridge import translate, smart_analyze, smart_transpile

def test_smart_analyze_simple():
    analysis = smart_analyze("T | where x == 1")
    assert analysis["strategy"] == "sql"
    assert analysis["recommended_engine"] == "spark"
    assert analysis["complexity"] < 5

def test_smart_analyze_complex_sql():
    analysis = smart_analyze("T1 | join (T2) on x | union T3 | where y == 2")
    assert analysis["strategy"] == "sql"
    assert analysis["recommended_engine"] == "spark"
    assert analysis["complexity"] >= 5

def test_smart_analyze_timeseries():
    analysis = smart_analyze("T | make-series count() on TimeGenerated from ago(1d) to now() step 1h")
    assert analysis["strategy"] == "timeseries"
    assert analysis["recommended_engine"] == "spark"
    assert analysis["complexity"] >= 6

def test_smart_analyze_dataframe():
    analysis = smart_analyze("T | extend a=1 | extend b=2 | extend c=3 | extend d=4")
    assert analysis["strategy"] == "dataframe"
    assert analysis["recommended_engine"] == "pyspark"

def test_translate_ignores_recommendation_and_respects_intent():
    # Recommended engine for T | extend a=1 | extend b=2 | extend c=3 | extend d=4
    # is "pyspark" (strategy: dataframe).
    # But translate() with target="tsql" must still output valid T-SQL!
    kql = "T | extend a=1 | extend b=2 | extend c=3 | extend d=4"
    sql = translate(kql, target="tsql")
    # Verify that the output is standard SQL syntax (no python/pyspark imports/display)
    assert "SELECT" in sql
    assert "df = spark" not in sql
    assert "display(" not in sql

def test_smart_transpile():
    engine, code = smart_transpile("T | where x == 1")
    assert engine == "spark_sql"
    assert "SELECT" in code
    
    # Forced engine
    engine2, code2 = smart_transpile("T | where x == 1", force_engine="tsql")
    assert engine2 == "tsql"
    assert "SELECT" in code2
