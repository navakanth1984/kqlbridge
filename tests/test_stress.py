import pytest
import sys
from kqlbridge import translate

# Skip stress tests in normal test runs to avoid slowing down CI
# unless explicitly requested, but for now we'll run them to prove resilience.
@pytest.mark.slow
def test_stress_massive_in_clause():
    """Verify the parser and generator can handle a massive IN clause without recursion errors."""
    items = ", ".join([f"'{i}'" for i in range(10000)])
    query = f"AppLogs | where RequestId in ({items})"
    sql = translate(query, target="spark")
    assert "IN (" in sql
    assert "'9999'" in sql


@pytest.mark.slow
def test_stress_deeply_nested_logical():
    """Verify the parser handles deeply nested boolean logic without hitting recursion limits."""
    # Lark's Earley parser handles deep recursion relatively well, but we should verify
    nested = "Level == 'Error'"
    for i in range(100):
        nested = f"({nested} or Level == 'Critical_{i}')"
    query = f"AppLogs | where {nested}"

    sql = translate(query, target="spark")
    assert "Critical_99" in sql
    assert "OR" in sql


@pytest.mark.slow
def test_stress_long_chained_pipes():
    """Verify the pipeline array builder doesn't crash on exceptionally long queries."""
    pipes = "\n".join([f"| extend X_{i} = {i}" for i in range(1000)])
    query = f"AppLogs \n {pipes}"

    sql = translate(query, target="spark")
    assert "X_999" in sql
    assert "AS X_999" in sql
