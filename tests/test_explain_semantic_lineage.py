from kqlbridge import explain_semantic, ExplainSemanticResult

def test_multi_hop_lineage_through_summarize():
    """Total -> B -> A -> X, Y - traces through dead summarize scope."""
    result = explain_semantic(
        "T | extend A = X + Y | extend B = A * 2 | summarize Total=sum(B)",
        target="spark"
    )
    
    assert isinstance(result, ExplainSemanticResult)
    assert result.target_dialect == "spark"
    assert len(result.symbols) == 1
    
    total = result.symbols[0]
    assert total.name == "Total"
    assert total.origin_node == "AggSum"
    
    assert len(total.dependencies) == 1
    b_node = total.dependencies[0]
    assert b_node.name == "B"
    assert b_node.origin_node == "ExtendOp"
    
    assert len(b_node.dependencies) == 1
    a_node = b_node.dependencies[0]
    assert a_node.name == "A"
    assert a_node.origin_node == "ExtendOp"
    
    assert len(a_node.dependencies) == 2
    deps = {d.name for d in a_node.dependencies}
    assert deps == {"X", "Y"}
    
    for d in a_node.dependencies:
        assert d.origin_node == "None"  # physical source columns in T
        assert len(d.dependencies) == 0

def test_explain_semantic_to_dict():
    """Verify that ExplainSemanticResult successfully serializes to dict."""
    result = explain_semantic(
        "T | extend A = X + Y | summarize Total=sum(A)",
        target="tsql"
    )
    
    data = result.to_dict()
    assert data["target_dialect"] == "tsql"
    assert len(data["symbols"]) == 1
    
    sym = data["symbols"][0]
    assert sym["name"] == "Total"
    assert sym["origin_node"] == "AggSum"
    assert len(sym["dependencies"]) == 1
    
    dep = sym["dependencies"][0]
    assert dep["name"] == "A"
    assert dep["origin_node"] == "ExtendOp"
    assert len(dep["dependencies"]) == 2
    
    child_names = {d["name"] for d in dep["dependencies"]}
    assert child_names == {"X", "Y"}

def test_explain_semantic_str_tree():
    """Verify the ASCII tree string representation of ExplainSemanticResult."""
    result = explain_semantic(
        "T | extend A = X + Y | summarize Total=sum(A)",
        target="spark"
    )
    
    tree_str = str(result)
    assert "Semantic Explanation Report [SPARK]" in tree_str
    assert "Total" in tree_str
    assert "└── A" in tree_str
    assert "    ├── X" in tree_str or "    └── X" in tree_str
    assert "    ├── Y" in tree_str or "    └── Y" in tree_str

def test_explain_semantic_warnings():
    """Verify that warnings flow through explain_semantic correctly."""
    result = explain_semantic(
        "T | where Level =~ 'error' | where Message has 'failed'",
        target="spark"
    )
    
    assert len(result.warnings) >= 2
    assert any("=~" in w for w in result.warnings)
    assert any("has" in w for w in result.warnings)
