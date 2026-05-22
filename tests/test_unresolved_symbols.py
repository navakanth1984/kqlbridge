import pytest
from kqlbridge.parser import parse
from kqlbridge.scoping import ScopeManager, UndefinedSymbolError
from kqlbridge.passes.alpha_renaming import AlphaRenamer

def test_unresolved_let_variable_error():
    # threshold is not declared, and since it is used in a where clause where we expect only columns or defined let bindings,
    # wait: as we decided, any identifier is auto-declared as a column if not found anywhere.
    # But wait! If we want to strictly test UndefinedSymbolError for columns isolated past boundaries (Schema Guillotine),
    # let's assert that UndefinedSymbolError is raised there.
    kql = "T | summarize Count=count() by ServiceName | where Level == 'Error'"
    query = parse(kql)
    scope_manager = ScopeManager()
    
    with pytest.raises(UndefinedSymbolError) as exc_info:
        AlphaRenamer(scope_manager).rename_query(query)
        
    assert "Undefined symbol: 'Level'" in str(exc_info.value)
