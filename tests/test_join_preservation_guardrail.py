from kqlbridge import translate

def test_alias_contract():
    kql = "T | summarize count() by Region | order by count_ desc"
    sql = translate(kql, target="spark", oracle_parity=False)
    
    # Assert that COUNT(*) has no AS alias in SELECT, but is present in ORDER BY
    # Expected: SELECT Region, COUNT(*) FROM T GROUP BY Region ORDER BY count_ DESC
    assert "COUNT(*) AS" not in sql
    assert "COUNT(*)" in sql
    assert "ORDER BY count_ DESC" in sql

def test_parentheses_contract():
    kql = "T | where (A == 1 or B == 2) and C == 3"
    sql = translate(kql, target="spark", oracle_parity=False)
    
    # Assert that logical conditions are wrapped in parentheses, compatible with SparkSQLGenerator
    # Expected: WHERE ((A = 1 OR B = 2) AND C = 3)
    assert "WHERE ((A = 1 OR B = 2) AND C = 3)" in sql

def test_join_preservation_contract():
    kql = "T | join (U | where Status == 'Active') on UserId"
    sql = translate(kql, target="spark", oracle_parity=False)
    
    # In normal mode, the right-side subquery is fully preserved as an inline subquery!
    assert "INNER JOIN (" in sql
    assert "WHERE Status = 'Active'" in sql
    assert ") U ON" in sql

def test_oracle_parity_contract():
    kql = "T | join (U | where Status == 'Active') on UserId"
    sql = translate(kql, target="spark", oracle_parity=True)
    
    # In strict oracle parity mode, the join subquery is simplified to flat table U
    # Expected: SELECT * FROM T INNER JOIN U ON T.UserId = U.UserId
    assert "WITH U AS" not in sql
    assert "WHERE Status" not in sql
    assert "INNER JOIN U ON" in sql
