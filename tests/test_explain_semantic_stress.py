from kqlbridge import explain_semantic

def test_recursive_self_reference():
    """Verify that shadowing a variable in subsequent extends (recursive self-reference) traces correctly without loops."""
    result = explain_semantic(
        "T | extend A = X | extend A = A + 1",
        target="spark"
    )
    
    assert len(result.symbols) >= 1
    # The visible output should have 'A' (shadowed)
    a_node = next(s for s in result.symbols if s.name == "A")
    assert a_node.origin_node == "ExtendOp"
    assert len(a_node.dependencies) == 1
    
    # Due to duplicate consecutive name-collapsing (A -> A -> X collapsing to A -> X),
    # the shadowed 'A' resolves directly to the original source column 'X'.
    x_node = a_node.dependencies[0]
    assert x_node.name == "X"
    assert x_node.origin_node == "None"
    assert len(x_node.dependencies) == 0

def test_nested_joins_lineage():
    """Verify that lineage traces column dependencies cleanly across join boundaries."""
    result = explain_semantic(
        "T1 | extend Key = X + 1 | join kind=inner (T2 | extend Key = Y + 2) on Key",
        target="spark"
    )
    
    assert len(result.symbols) >= 1
    # Check that 'Key' exists in the outputs and traces back to its source columns
    key_nodes = [s for s in result.symbols if s.name == "Key"]
    assert len(key_nodes) >= 1
    
    # Trace the left Key
    left_key = key_nodes[0]
    assert left_key.name == "Key"
    assert len(left_key.dependencies) == 1
    assert left_key.dependencies[0].name == "X"

def test_nested_unions_lineage():
    """Verify that column lineages trace cleanly across subqueries inside a union pipeline."""
    result = explain_semantic(
        "T1 | extend A = X + 1 | union (T2 | extend A = Y + 2)",
        target="spark"
    )
    
    assert len(result.symbols) >= 1
    a_nodes = [s for s in result.symbols if s.name == "A"]
    assert len(a_nodes) >= 1

def test_multi_level_let_chains():
    """Verify multi-level let chains correctly trace dependencies across multiple CTE definitions."""
    result = explain_semantic(
        "let A = T | extend X = 1; let B = A | extend Y = X + 2; B | extend Z = Y + 3",
        target="spark"
    )
    
    assert len(result.symbols) >= 1
    z_node = next(s for s in result.symbols if s.name == "Z")
    assert z_node.name == "Z"
    assert len(z_node.dependencies) == 1
    
    y_node = z_node.dependencies[0]
    assert y_node.name == "Y"
    assert len(y_node.dependencies) == 1
    
    x_node = y_node.dependencies[0]
    assert x_node.name == "X"

def test_duplicate_aliases_shadowing():
    """Verify that re-extending or duplicating aliases resolves to the correct step-specific symbol IDs."""
    result = explain_semantic(
        "T | extend A = X | extend A = Y",
        target="spark"
    )
    
    assert len(result.symbols) >= 1
    a_node = next(s for s in result.symbols if s.name == "A")
    assert a_node.name == "A"
    assert len(a_node.dependencies) == 1
    
    # The latest 'A' should derive from 'Y'
    dep = a_node.dependencies[0]
    assert dep.name == "Y"
    assert dep.origin_node == "None"
