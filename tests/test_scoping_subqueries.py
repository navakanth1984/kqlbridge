import pytest
from kqlbridge import translate
from kqlbridge.parser import parse
from kqlbridge.scoping import ScopeManager, UndefinedSymbolError
from kqlbridge.passes.alpha_renaming import AlphaRenamer

def test_subquery_let_inheritance():
    # Verify subqueries inherit parent LET variables
    kql = """
    let common_thresh = 10;
    TableA
    | join kind=inner (TableB | where BCol > common_thresh) on Key
    """
    # Should compile successfully
    res = translate(kql, target="spark")
    assert "common_thresh" in res or "10" in res

def test_subquery_column_isolation():
    # Verify subqueries are strictly blocked from resolving outer pipeline columns.
    # Here, "outer_col" is defined in the outer pipeline before join.
    # TableB inside the join subquery should NOT be able to resolve outer_col.
    kql = """
    TableA
    | extend outer_col = 5
    | join kind=inner (TableB | where BCol > outer_col) on Key
    """
    
    query = parse(kql)
    scope_manager = ScopeManager()
    
    with pytest.raises(UndefinedSymbolError) as exc_info:
        AlphaRenamer(scope_manager).rename_query(query)
    
    assert "Undefined symbol: 'outer_col'" in str(exc_info.value)
