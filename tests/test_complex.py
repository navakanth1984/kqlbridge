import pytest
from kqlbridge import translate, detect_operators, is_supported

def test_unsupported_operators():
    """Verify that unsupported operators are correctly flagged by is_supported."""
    unsupported_queries = [
        "AppLogs | make-series count() on TimeGenerated from ago(7d) to now() step 1d",
        "AppLogs | render timechart",
        "Events | evaluate bag_unpack(properties)",
    ]
    for q in unsupported_queries:
        assert is_supported(q) is False


def test_detect_multiple_operators():
    """Verify detect_operators correctly identifies operators in a complex pipeline."""
    complex_query = """
    AppLogs
    | where Level == 'Error' and TimeGenerated > ago(7d)
    | project TimeGenerated, ServiceName, Message, RequestId
    | join kind=inner (
        Requests | where DurationMs > 1000
    ) on RequestId
    | summarize ErrorCount=count(), AvgDuration=avg(DurationMs) by ServiceName
    | order by ErrorCount desc
    | take 10
    """
    ops = detect_operators(complex_query)
    # detect_operators currently inspects the main pipeline's pipes
    assert ops == ["where", "project", "join", "summarize", "order by", "take"]


def test_translate_complex_pipeline():
    """Verify a complex KQL query successfully translates to valid Spark SQL."""
    complex_query = """
    AppLogs
    | where TimeGenerated > ago(1d)
    | extend IsCritical = iff(Level == 'Critical', true, false)
    | summarize Total=count(), CriticalCount=countif(IsCritical == true) by bin(TimeGenerated, 1h), ServiceName
    | order by Total desc
    """

    assert is_supported(complex_query) is True

    sql = translate(complex_query, target="spark")

    # Check for presence of expected SQL fragments
    assert "CASE WHEN" in sql
    assert "DATE_TRUNC" in sql
    assert "GROUP BY" in sql
    assert "ORDER BY" in sql

    # Run the sqlglot syntax check to ensure it's structurally valid Spark SQL
    try:
        import sqlglot
        parsed = sqlglot.parse(sql, dialect="spark")
        assert len(parsed) > 0
    except ImportError:
        pass
