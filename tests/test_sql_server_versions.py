from kqlbridge import translate, CompilerOptions

def test_tsql_binning_legacy_2019():
    kql = "SecurityEvents | summarize count() by bin(TimeGenerated, 1h)"
    
    # 2019 legacy target
    options = CompilerOptions(sql_server_version=2019)
    sql = translate(kql, target="tsql", options=options)
    
    # Assert DATEADD/DATEDIFF legacy pattern
    assert "DATEADD" in sql or "dateadd" in sql
    assert "DATEDIFF" in sql or "datediff" in sql
    assert "DATETRUNC" not in sql and "datetrunc" not in sql

def test_tsql_binning_modern_2022():
    kql = "SecurityEvents | summarize count() by bin(TimeGenerated, 1h)"
    
    # 2022 modern target
    options = CompilerOptions(sql_server_version=2022)
    sql = translate(kql, target="tsql", options=options)
    
    # Assert DATETRUNC modern pattern
    assert "DATETRUNC" in sql or "datetrunc" in sql
    assert "DATEADD" not in sql and "dateadd" not in sql
