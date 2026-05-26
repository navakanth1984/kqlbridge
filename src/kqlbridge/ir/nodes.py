from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from ..scoping import SymbolTable

class SemanticIRNode:
    """Base structural class for all KQLBridge Intermediate Representation nodes."""
    pass

class SemanticExpression(SemanticIRNode):
    """Base structural class for all normalized Semantic Expressions."""
    pass

@dataclass(slots=True)
class SemanticColumnRef(SemanticExpression):
    """Reference to a transient physical or resolved logical column."""
    name: str
    symbol_id: int

@dataclass(slots=True)
class SemanticLiteral(SemanticExpression):
    """Literal constant value (String, Int, Float, Bool, Datetime)."""
    value: Any

@dataclass(slots=True)
class SemanticComparison(SemanticExpression):
    """Comparison expression between two operands."""
    left: SemanticExpression
    op: str
    right: SemanticExpression

@dataclass(slots=True)
class SemanticLogicalOp(SemanticExpression):
    """Boolean logical operation (e.g. AND, OR, NOT)."""
    op: str
    expressions: List[SemanticExpression]

@dataclass(slots=True)
class SemanticBinaryOp(SemanticExpression):
    """Arithmetic or binary operator (+, -, *, /)."""
    left: SemanticExpression
    operator: str
    right: SemanticExpression

@dataclass(slots=True)
class SemanticUnaryOp(SemanticExpression):
    """Unary operator (e.g. -x)."""
    operator: str
    expression: SemanticExpression

@dataclass(slots=True)
class SemanticFunctionCall(SemanticExpression):
    """Normalized function call (scalar, type conversion, timespan arithmetic)."""
    name: str
    arguments: List[SemanticExpression]

    @property
    def args(self) -> List[SemanticExpression]:
        """Alias for compatibility with AST-based generators."""
        return self.arguments

@dataclass(slots=True)
class SemanticIndexedAccess(SemanticExpression):
    """Array or dynamic map indexing (e.g. col[0], col['key'])."""
    expression: SemanticExpression
    index: SemanticExpression

@dataclass(slots=True)
class SemanticPropertyAccess(SemanticExpression):
    """Dynamic property or member access (e.g. col.prop)."""
    expression: SemanticExpression
    property: str

@dataclass(slots=True)
class SemanticSubquery(SemanticExpression):
    """Nested subquery scan block, often used in in-operators or subquery expressions."""
    query: 'SemanticQuery'

@dataclass(slots=True)
class SemanticQuery(SemanticIRNode):
    """
    The top-level relational engine envelope.
    Coordinates source states, pipeline tracking stages, and common table expressions.
    """
    source: Union[str, 'SemanticQuery', List[str]]
    steps: List[SemanticIRNode] = field(default_factory=list)
    ctes: Dict[str, 'SemanticQuery'] = field(default_factory=dict)
    symbol_table: Optional[SymbolTable] = None
    pipeline_state: Dict[str, Any] = field(default_factory=dict)
    query_id: int = 0
    lineage_graph: Optional[Any] = None
    scalar_bindings: Dict[str, Any] = field(default_factory=dict)

    @property
    def source_table(self) -> str:
        if isinstance(self.source, str):
            return self.source
        elif isinstance(self.source, SemanticQuery):
            return self.source.source_table
        elif isinstance(self.source, list) and self.source:
            first = self.source[0]
            return first if isinstance(first, str) else ""
        return ""

@dataclass(slots=True)
class SemanticFilter(SemanticIRNode):
    """Normalizes boolean evaluation predicates into clean logical conditions."""
    predicate: SemanticExpression
    origin_node: Any = None

@dataclass(slots=True)
class ProjectionItem:
    """Tracks a single projected attribute column element, its identity index, and origins."""
    alias: str
    expression: SemanticExpression
    symbol_id: int
    derived_from: List[int] = field(default_factory=list)
    origin_node: Any = None

@dataclass(slots=True)
class SemanticProjection(SemanticIRNode):
    """Represents an explicit relational projection operation specifying output tuple arrays."""
    items: List[ProjectionItem]
    is_extend_only: bool = False

@dataclass(slots=True)
class AggregateItem:
    """Represents a calculated aggregate expression metric."""
    alias: str
    function_name: str
    arguments: List[SemanticExpression]
    symbol_id: int
    derived_from: List[int] = field(default_factory=list)
    origin_node: Any = None
    is_distinct: bool = False

@dataclass(slots=True)
class SemanticAggregate(SemanticIRNode):
    """Standardizes metric groupings and computed outputs."""
    aggregations: List[AggregateItem]
    group_by: List[ProjectionItem]

@dataclass(slots=True)
class SemanticJoinCondition:
    """Tracks a single column mapping predicate in a Join operation."""
    left_symbol_id: int
    right_symbol_id: int
    left_col: str
    right_col: str
    operator: str = "=="

@dataclass(slots=True)
class SemanticJoin(SemanticIRNode):
    """Expanded relational Join intermediate representation node."""
    right_query: 'SemanticQuery'
    right_alias: str
    kind: str  # e.g., 'inner', 'leftouter'
    conditions: List[SemanticJoinCondition] = field(default_factory=list)
    on_keys: List[str] = field(default_factory=list)

@dataclass(slots=True)
class UnionColumnMapping:
    """Represents an aligned column and its sources in a Union operation."""
    output_alias: str
    source_mappings: Dict[int, Optional[int]]  # branch_idx -> symbol_id
    is_nullable: bool = True

@dataclass(slots=True)
class SemanticUnion(SemanticIRNode):
    """Expanded relational Union intermediate representation node."""
    tables: List[str]
    inputs: List['SemanticQuery'] = field(default_factory=list)
    mappings: List[UnionColumnMapping] = field(default_factory=list)
    subqueries: Dict[str, 'SemanticQuery'] = field(default_factory=dict)
