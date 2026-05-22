import pytest
from kqlbridge.parser import parse
from kqlbridge.scoping import ScopeManager, UndefinedSymbolError
from kqlbridge.passes.alpha_renaming import AlphaRenamer

def test_summarize_schema_guillotine_blocked():
    # ServiceName and Count are valid downstream, but Level is truncated/blocked
    kql = "T | summarize Count=count() by ServiceName | where Level == 'Error'"
    query = parse(kql)
    scope_manager = ScopeManager()
    
    with pytest.raises(UndefinedSymbolError) as exc_info:
        AlphaRenamer(scope_manager).rename_query(query)
        
    assert "Undefined symbol: 'Level'" in str(exc_info.value)

def test_summarize_schema_guillotine_allowed():
    # ServiceName and Count are valid downstream because they are grouping keys / aggregation outputs
    kql = "T | summarize Count=count() by ServiceName | where ServiceName == 'API' and Count > 10"
    query = parse(kql)
    scope_manager = ScopeManager()
    
    # Should compile/rename successfully without UndefinedSymbolError
    query = AlphaRenamer(scope_manager).rename_query(query)
    assert query is not None

def test_summarize_implicit_aliases():
    # count() gets implicit alias count_ and is valid downstream
    kql = "T | summarize count() by ServiceName | where count_ > 10"
    query = parse(kql)
    scope_manager = ScopeManager()
    
    # Should compile/rename successfully without UndefinedSymbolError
    query = AlphaRenamer(scope_manager).rename_query(query)
    assert query is not None
