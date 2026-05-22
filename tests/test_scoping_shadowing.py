import pytest
from kqlbridge import translate
from kqlbridge.parser import parse
from kqlbridge.scoping import ScopeManager
from kqlbridge.passes.alpha_renaming import AlphaRenamer
from kqlbridge.passes.constant_folding import ConstantFolder

def test_lexical_shadowing_alpha_renaming():
    kql = "let threshold = 100; AppLogs | extend threshold = threshold + 5"
    query = parse(kql)
    scope_manager = ScopeManager()
    
    # Apply alpha renaming
    query = AlphaRenamer(scope_manager).rename_query(query)
    
    # The LHS in extend should be renamed because it shadows the global let binding "threshold"
    extend_op = query.pipes[0]
    assigned_name, assigned_expr = extend_op.assignments[0]
    
    assert assigned_name != "threshold"
    assert "kqlbridge_sym" in assigned_name
    # The RHS threshold should resolve to the global let binding, which is not renamed because it has no collision at its definition
    assert assigned_expr.left.name == "threshold"

def test_shadowing_translation():
    kql = "let threshold = 100; AppLogs | extend threshold = threshold + 5"
    res = translate(kql, target="spark")
    
    # Should compile successfully and include the renamed symbol
    assert "__kqlbridge_sym_" in res

def test_symbol_leakage_nightmare_nested():
    kql = """
    let threshold = 10;
    A
    | extend threshold = 5
    | join (
        B
        | extend threshold = 20
    ) on key
    """
    query = parse(kql)
    scope_manager = ScopeManager()
    query = AlphaRenamer(scope_manager).rename_query(query)
    
    # Global let binding
    assert query.let_bindings[0].name == "threshold"
    
    # Main pipeline extend operator
    main_extend = query.pipes[0]
    main_assigned_name, _ = main_extend.assignments[0]
    assert "sym" in main_assigned_name
    assert main_assigned_name != "threshold"
    
    # Join subquery extend operator
    join_op = query.pipes[1]
    join_extend = join_op.right.pipes[0]
    join_assigned_name, _ = join_extend.assignments[0]
    assert "sym" in join_assigned_name
    assert join_assigned_name != "threshold"
    
    # Ensure they are distinct unique symbols
    assert main_assigned_name != join_assigned_name
