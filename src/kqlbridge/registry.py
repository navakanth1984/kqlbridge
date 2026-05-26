from __future__ import annotations
from enum import Enum
from typing import Dict

class CapabilityLevel(Enum):
    NATIVE = "NATIVE"
    EMULATED = "EMULATED"
    PARTIAL = "PARTIAL"
    UNSUPPORTED = "UNSUPPORTED"

# Declarative support matrix mapping dialect targets to KQL operators and functions
SUPPORT_MATRIX: Dict[str, Dict[str, CapabilityLevel]] = {
    "spark": {
        "where": CapabilityLevel.NATIVE,
        "project": CapabilityLevel.NATIVE,
        "summarize": CapabilityLevel.NATIVE,
        "order by": CapabilityLevel.NATIVE,
        "sort by": CapabilityLevel.NATIVE,
        "take": CapabilityLevel.NATIVE,
        "limit": CapabilityLevel.NATIVE,
        "distinct": CapabilityLevel.NATIVE,
        "extend": CapabilityLevel.NATIVE,
        "join": CapabilityLevel.PARTIAL,  # Only standard inner/left/right/full kinds supported
        "union": CapabilityLevel.NATIVE,
        "count": CapabilityLevel.NATIVE,
        "make-series": CapabilityLevel.EMULATED,  # Emulated via TimeSeriesMicroModel
        "series_fill_linear": CapabilityLevel.EMULATED,
        "series_fill_forward": CapabilityLevel.EMULATED,
        "series_decompose_anomalies": CapabilityLevel.UNSUPPORTED,
        "bag_unpack": CapabilityLevel.UNSUPPORTED,
        "render": CapabilityLevel.UNSUPPORTED,
        "ipv4_is_in_range": CapabilityLevel.UNSUPPORTED,
        "udf": CapabilityLevel.UNSUPPORTED,
    },
    "tsql": {
        "where": CapabilityLevel.NATIVE,
        "project": CapabilityLevel.NATIVE,
        "summarize": CapabilityLevel.NATIVE,
        "order by": CapabilityLevel.NATIVE,
        "sort by": CapabilityLevel.NATIVE,
        "take": CapabilityLevel.NATIVE,
        "limit": CapabilityLevel.NATIVE,
        "distinct": CapabilityLevel.NATIVE,
        "extend": CapabilityLevel.NATIVE,
        "join": CapabilityLevel.PARTIAL,
        "union": CapabilityLevel.NATIVE,
        "count": CapabilityLevel.NATIVE,
        "make-series": CapabilityLevel.EMULATED,
        "series_fill_linear": CapabilityLevel.EMULATED,
        "series_fill_forward": CapabilityLevel.EMULATED,
        "series_decompose_anomalies": CapabilityLevel.UNSUPPORTED,
        "bag_unpack": CapabilityLevel.UNSUPPORTED,
        "render": CapabilityLevel.UNSUPPORTED,
        "ipv4_is_in_range": CapabilityLevel.UNSUPPORTED,
        "udf": CapabilityLevel.UNSUPPORTED,
    },
    "pyspark": {
        "where": CapabilityLevel.NATIVE,
        "project": CapabilityLevel.NATIVE,
        "summarize": CapabilityLevel.NATIVE,
        "order by": CapabilityLevel.NATIVE,
        "sort by": CapabilityLevel.NATIVE,
        "take": CapabilityLevel.NATIVE,
        "limit": CapabilityLevel.NATIVE,
        "distinct": CapabilityLevel.NATIVE,
        "extend": CapabilityLevel.NATIVE,
        "join": CapabilityLevel.PARTIAL,
        "union": CapabilityLevel.NATIVE,
        "count": CapabilityLevel.NATIVE,
        "make-series": CapabilityLevel.EMULATED,
        "series_fill_linear": CapabilityLevel.EMULATED,
        "series_fill_forward": CapabilityLevel.EMULATED,
        "series_decompose_anomalies": CapabilityLevel.UNSUPPORTED,
        "bag_unpack": CapabilityLevel.UNSUPPORTED,
        "render": CapabilityLevel.UNSUPPORTED,
        "ipv4_is_in_range": CapabilityLevel.UNSUPPORTED,
        "udf": CapabilityLevel.UNSUPPORTED,
    }
}

def get_capability_level(operator: str, target: str) -> CapabilityLevel:
    """
    Retrieve the precise capability support level of a KQL operator/function for a target dialect.
    
    Args:
        operator: KQL operator name (e.g. 'summarize', 'make-series').
        target: Target dialect name (e.g. 'spark', 'tsql', 'pyspark').
    
    Returns:
        CapabilityLevel enum indicating native, emulated, partial, or unsupported status.
    """
    target = target.lower()
    operator = operator.lower()
    
    dialect_matrix = SUPPORT_MATRIX.get(target)
    if not dialect_matrix:
        return CapabilityLevel.UNSUPPORTED
        
    return dialect_matrix.get(operator, CapabilityLevel.UNSUPPORTED)

def is_operator_supported(operator: str, target: str) -> bool:
    """
    Determine if a KQL operator is supported (Native, Emulated, or Partial) under the specified target.
    
    Args:
        operator: KQL operator name.
        target: Target dialect name.
        
    Returns:
        True if supported in any shape, False if UNSUPPORTED.
    """
    level = get_capability_level(operator, target)
    return level != CapabilityLevel.UNSUPPORTED

def get_supported_dialects(operator: str) -> Dict[str, CapabilityLevel]:
    """
    Get all target dialects and their capability support levels for a given KQL operator.
    
    Args:
        operator: KQL operator name.
        
    Returns:
        Dict mapping dialect name to CapabilityLevel.
    """
    operator = operator.lower()
    result = {}
    for dialect, ops in SUPPORT_MATRIX.items():
        level = ops.get(operator, CapabilityLevel.UNSUPPORTED)
        result[dialect] = level
    return result
