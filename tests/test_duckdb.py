import pytest
import pandas as pd
from kqlbridge.verify import verify, VerificationResult

def test_duckdb_local_verify():
    # Setup in-memory reference DataFrame
    reference_df = pd.DataFrame({
        "TimeGenerated": ["2026-05-23T08:00:00Z", "2026-05-23T09:00:00Z"],
        "Level": ["Error", "Warning"],
        "Computer": ["svr1", "svr2"]
    })
    
    # 1. Matching case
    kql = "T | where Level == 'Error'"
    expected_ref = pd.DataFrame({
        "TimeGenerated": ["2026-05-23T08:00:00Z"],
        "Level": ["Error"],
        "Computer": ["svr1"]
    })
    
    result = verify(kql, expected_ref)
    assert isinstance(result, VerificationResult)
    assert result.is_matching is True
    assert result.row_count_match is True
    assert result.schema_match is True
    assert result.details["rows"] == 1
    assert result.details["columns"] == ["TimeGenerated", "Level", "Computer"]

def test_duckdb_local_verify_mismatch():
    # Setup in-memory reference DataFrame
    reference_df = pd.DataFrame({
        "TimeGenerated": ["2026-05-23T08:00:00Z", "2026-05-23T09:00:00Z"],
        "Level": ["Error", "Warning"],
        "Computer": ["svr1", "svr2"]
    })
    
    # Mismatched rows count case
    kql = "T | where Level == 'Error'"
    result = verify(kql, reference_df)  # comparing 1 row result to 2 row reference
    assert result.is_matching is False
    assert result.row_count_match is False
    assert result.schema_match is True
