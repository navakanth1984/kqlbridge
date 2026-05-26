from __future__ import annotations
from kqlbridge.parser import parse
from kqlbridge.optimizer import ASTOptimizer
from kqlbridge.ast_nodes import WhereOp, OrderOp, ExtendOp, ProjectOp, SummarizeOp, JoinOp
from kqlbridge import translate

def test_ast_optimizer_non_mutation():
    # Parse KQL query to obtain original AST
    kql = "T | where x == 1 | order by y asc"
    query = parse(kql)
    
    # Run optimization
    opt = ASTOptimizer()
    optimized = opt.optimize(query)
    
    # Assert they are separate instances (non-mutation)
    assert query is not optimized
    assert id(query) != id(optimized)
    # Ensure pipes list and its contents are deepcopied/cloned
    assert query.pipes is not optimized.pipes
    assert query.pipes[0] is not optimized.pipes[0]

def test_merge_filters_optimization():
    # Consecutive filters should merge
    kql = "T | where x == 1 | where y == 2"
    sql = translate(kql, target="spark")
    
    # The output SQL should show them combined in a single WHERE clause
    # without generating nested query blocks
    assert "WHERE" in sql
    assert "AND" in sql
    assert "(_filtered" not in sql
    
    # Parse and inspect AST directly
    query = parse(kql)
    optimized = ASTOptimizer().optimize(query)
    # The two WhereOp nodes should be merged into 1 WhereOp node
    where_ops = [op for op in optimized.pipes if isinstance(op, WhereOp)]
    assert len(where_ops) == 1

def test_predicate_pushdown_past_order_by():
    # "where" after "order by" should swap places
    kql = "T | order by x asc | where y == 2"
    query = parse(kql)
    optimized = ASTOptimizer().optimize(query)
    
    # The optimized pipeline should have WhereOp first, then OrderOp
    assert isinstance(optimized.pipes[0], WhereOp)
    assert isinstance(optimized.pipes[1], OrderOp)

def test_predicate_pushdown_past_extend():
    # Filter on unrelated column should swap with extend
    kql1 = "T | extend z = x + 1 | where y == 2"
    q1 = parse(kql1)
    opt1 = ASTOptimizer().optimize(q1)
    assert isinstance(opt1.pipes[0], WhereOp)
    assert isinstance(opt1.pipes[1], ExtendOp)
    
    # Filter on extended column should NOT swap with extend
    kql2 = "T | extend z = x + 1 | where z == 2"
    q2 = parse(kql2)
    opt2 = ASTOptimizer().optimize(q2)
    assert isinstance(opt2.pipes[0], ExtendOp)
    assert isinstance(opt2.pipes[1], WhereOp)

def test_predicate_pushdown_past_project():
    # Filter on unrelated column should swap with project
    kql1 = "T | project x, y = a | where x == 2"
    q1 = parse(kql1)
    opt1 = ASTOptimizer().optimize(q1)
    assert isinstance(opt1.pipes[0], WhereOp)
    assert isinstance(opt1.pipes[1], ProjectOp)
    
    # Filter on aliased column (y) should NOT swap with project
    kql2 = "T | project x, y = a | where y == 2"
    q2 = parse(kql2)
    opt2 = ASTOptimizer().optimize(q2)
    assert isinstance(opt2.pipes[0], ProjectOp)
    assert isinstance(opt2.pipes[1], WhereOp)

def test_optimizer_lineage_safety_audit():
    # 1. Extend lineage: Filter on extended column (X) must NOT swap with extend
    kql_ext = "T | extend X = A + B | where X > 10"
    q_ext = parse(kql_ext)
    opt_ext = ASTOptimizer().optimize(q_ext)
    assert isinstance(opt_ext.pipes[0], ExtendOp)
    assert isinstance(opt_ext.pipes[1], WhereOp)

    # 2. Project aliases lineage: Filter on project alias (y) must NOT swap with project
    kql_proj = "T | project x, y = a | where y == 2"
    q_proj = parse(kql_proj)
    opt_proj = ASTOptimizer().optimize(q_proj)
    assert isinstance(opt_proj.pipes[0], ProjectOp)
    assert isinstance(opt_proj.pipes[1], WhereOp)

    # 3. Summarize aliases lineage: Filter on summarize grouping/aggregated column must NOT swap with summarize
    kql_sum = "T | summarize Count = count() by Category | where Count > 10"
    q_sum = parse(kql_sum)
    opt_sum = ASTOptimizer().optimize(q_sum)
    assert isinstance(opt_sum.pipes[0], SummarizeOp)
    assert isinstance(opt_sum.pipes[1], WhereOp)

    # 4. Join generated columns lineage: Filter on joined table columns must NOT swap with join
    kql_join = "T1 | join (T2) on Key | where T2_Col == 1"
    q_join = parse(kql_join)
    opt_join = ASTOptimizer().optimize(q_join)
    assert isinstance(opt_join.pipes[0], JoinOp)
    assert isinstance(opt_join.pipes[1], WhereOp)

