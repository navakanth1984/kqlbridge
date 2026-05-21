from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Dict

@dataclass
class WindowSpec:
    """
    Configuration specification for SQL window functions (e.g. LAG, LEAD).
    
    Attributes:
        partition_by: List of column names or expressions to partition by.
        order_by: List of column names or expressions (with optional direction, e.g. "Col DESC") to order by.
    """
    partition_by: Optional[List[str]] = None
    order_by: Optional[List[str]] = None

@dataclass
class SchemaHint:
    """
    Call-level hint mapping containing metadata about the source schema context.
    
    Attributes:
        window_spec: Custom window partitioning and ordering configurations.
        json_fields: Explicit dictionary metadata mapping for parsing JSON fields.
        target_dialect: Override or specific target engine SQL dialect.
    """
    window_spec: Optional[WindowSpec] = None
    json_fields: Optional[Dict] = None
    target_dialect: Optional[str] = None
