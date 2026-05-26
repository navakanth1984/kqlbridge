from kqlbridge.parser import parse
from kqlbridge.scoping import ScopeManager
from kqlbridge.passes.alpha_renaming import AlphaRenamer
from kqlbridge.passes.constant_folding import ConstantFolder
from kqlbridge.ast_nodes import IntLit, FloatLit, BoolLit, StringLit

def test_static_arithmetic_folding():
    # 5 + 5 should fold to 10
    kql = "let threshold = 5 + 5; T | extend res = threshold"
    query = parse(kql)
    scope_manager = ScopeManager()
    
    query = AlphaRenamer(scope_manager).rename_query(query)
    query = ConstantFolder(scope_manager).fold_query(query)
    
    # Check that threshold let binding value was folded to 10
    let_val = query.let_bindings[0].value.scalar_expr
    assert isinstance(let_val, IntLit)
    assert let_val.value == 10
    
    # Check that res assignment was substituted with 10
    extend_op = query.pipes[0]
    assigned_name, assigned_expr = extend_op.assignments[0]
    assert isinstance(assigned_expr, IntLit)
    assert assigned_expr.value == 10
    
    # Check lineage metadata preservation
    assert hasattr(assigned_expr, "metadata")
    assert assigned_expr.metadata["name"] == "threshold"
    assert assigned_expr.metadata["symbol_kind"] == "LET"

def test_pure_function_folding():
    kql = "let msg = strcat('Hello', ' ', 'World'); T | extend res = msg"
    query = parse(kql)
    scope_manager = ScopeManager()
    
    query = AlphaRenamer(scope_manager).rename_query(query)
    query = ConstantFolder(scope_manager).fold_query(query)
    
    # check that it folded to StringLit("Hello World")
    let_val = query.let_bindings[0].value.scalar_expr
    assert isinstance(let_val, StringLit)
    assert let_val.value == "Hello World"
    
    extend_op = query.pipes[0]
    assigned_name, assigned_expr = extend_op.assignments[0]
    assert isinstance(assigned_expr, StringLit)
    assert assigned_expr.value == "Hello World"

def test_runtime_eviction_from_folding():
    # ago(1h) is context-dependent and should NOT be folded
    kql = "let t = ago(1h); T | where TimeGenerated > t"
    query = parse(kql)
    scope_manager = ScopeManager()
    
    query = AlphaRenamer(scope_manager).rename_query(query)
    query = ConstantFolder(scope_manager).fold_query(query)
    
    # Let binding t should still be an AgoExpr (or equivalent)
    let_val = query.let_bindings[0].value.scalar_expr
    assert not isinstance(let_val, (IntLit, FloatLit, StringLit, BoolLit))
    
    # Where condition should not have been replaced by a folded primitive literal
    where_op = query.pipes[0]
    assert not isinstance(where_op.condition.right, (IntLit, FloatLit, StringLit, BoolLit))
