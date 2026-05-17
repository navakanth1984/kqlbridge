import pytest
from kqlbridge import translate

def sql(kql: str) -> str:
    return translate(kql, target="tsql")

def test_top():
    result = sql("AppLogs | take 100")
    assert "TOP 100" in result
    assert "LIMIT" not in result

def test_bin():
    result = sql("AppLogs | summarize count() by bin(TimeGenerated, 1h)")
    assert "DATEADD(hour, DATEDIFF(hour, 0, TimeGenerated), 0)" in result

def test_ago():
    result = sql("AppLogs | where TimeGenerated > ago(24h)")
    assert "DATEADD(hour, -24, GETDATE())" in result

def test_bool():
    result = sql("AppLogs | extend IsError = true")
    assert "1 AS IsError" in result

def test_datetime():
    result = sql("AppLogs | where TimeGenerated > datetime('2023-01-01T00:00:00Z')")
    assert "CONVERT(datetime, '2023-01-01T00:00:00Z')" in result
