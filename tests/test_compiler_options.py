from kqlbridge import translate, CompilerOptions

def test_compiler_options_flow():
    # Verify standard translation flows cleanly
    kql = "T | where X == 1"
    options = CompilerOptions(oracle_parity=False)
    sql = translate(kql, target="spark", options=options)
    assert "WHERE" in sql

def test_compiler_options_oracle_parity_explicit():
    # Verify explicit oracle_parity=True simplifies joins
    kql = "T | join (U | where Status == 'Active') on UserId"
    options = CompilerOptions(oracle_parity=True)
    sql = translate(kql, target="spark", options=options)
    
    # Assert it was simplified (no CTE, flat join table)
    assert "WITH U AS" not in sql
    assert "INNER JOIN U ON" in sql

def test_compiler_options_oracle_parity_explicit_false():
    # Verify explicit oracle_parity=False preserves join subqueries inline
    kql = "T | join (U | where Status == 'Active') on UserId"
    options = CompilerOptions(oracle_parity=False)
    sql = translate(kql, target="spark", options=options)
    
    # Assert it preserved the subquery inline
    assert "INNER JOIN (" in sql
    assert "WHERE Status = 'Active'" in sql
