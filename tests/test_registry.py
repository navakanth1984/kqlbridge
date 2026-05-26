from __future__ import annotations
from kqlbridge.registry import (
    CapabilityLevel, get_capability_level, is_operator_supported, get_supported_dialects
)

def test_capability_levels():
    # Verify standard operator mappings
    assert get_capability_level("where", "spark") == CapabilityLevel.NATIVE
    assert get_capability_level("summarize", "tsql") == CapabilityLevel.NATIVE
    assert get_capability_level("make-series", "pyspark") == CapabilityLevel.EMULATED
    assert get_capability_level("join", "spark") == CapabilityLevel.PARTIAL
    assert get_capability_level("bag_unpack", "spark") == CapabilityLevel.UNSUPPORTED

def test_is_operator_supported():
    assert is_operator_supported("where", "spark") is True
    assert is_operator_supported("make-series", "tsql") is True
    assert is_operator_supported("bag_unpack", "spark") is False
    # Case insensitivity
    assert is_operator_supported("WHERE", "Spark") is True

def test_get_supported_dialects():
    dialects = get_supported_dialects("where")
    assert dialects["spark"] == CapabilityLevel.NATIVE
    assert dialects["tsql"] == CapabilityLevel.NATIVE
    assert dialects["pyspark"] == CapabilityLevel.NATIVE
    
    dialects_series = get_supported_dialects("make-series")
    assert dialects_series["spark"] == CapabilityLevel.EMULATED
