"""
ast_nodes.py — KQLBridge Typed AST Node Definitions
====================================================
LOCKED FILE — Human-designed. Agent MUST NEVER modify this file.

These dataclasses form the stable intermediate representation between
the parser (which reads the lark parse tree) and the generators (which
emit target SQL). They must remain stable across all operator additions.

Adding a new operator = add a new dataclass here (human decision),
then implement it in parser.py and generator.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Union


# ─── Scalar Expressions ──────────────────────────────────────────────────────

@dataclass
class ColumnRef:
    """A reference to a column: e.g. ServiceName"""
    name: str


@dataclass
class StringLit:
    """A string literal: 'Error' or "Error" """
    value: str


@dataclass
class IntLit:
    """An integer literal: 100"""
    value: int


@dataclass
class FloatLit:
    """A float literal: 3.14"""
    value: float


@dataclass
class BoolLit:
    """A boolean literal: true / false"""
    value: bool


@dataclass
class DatetimeLit:
    """A KQL datetime literal: datetime(2024-01-01)"""
    raw: str


@dataclass
class AgoExpr:
    """KQL ago(1h) → CURRENT_TIMESTAMP - INTERVAL '1 hours'"""
    amount: int
    unit: str  # 'd', 'h', 'm', 's'


@dataclass
class BinExpr:
    """KQL bin(col, 1h) → DATE_TRUNC('hour', col)"""
    col: "Expr"
    amount: int
    unit: str  # 'd', 'h', 'm', 's'


@dataclass
class FuncCall:
    """A generic function call: tostring(x), strlen(x)"""
    name: str
    args: list["Expr"]


@dataclass
class BinaryOp:
    """Arithmetic: a + b, a - b, a * b, a / b"""
    left: "Expr"
    op: str
    right: "Expr"


# Expr = any scalar expression type
Expr = Union[
    ColumnRef, StringLit, IntLit, FloatLit, BoolLit, DatetimeLit,
    AgoExpr, BinExpr, FuncCall, BinaryOp
]


# ─── Boolean / Filter Expressions ────────────────────────────────────────────

@dataclass
class Comparison:
    """col == 'Error', TimeGenerated > ago(1h)"""
    left: Expr
    op: str   # '==', '!=', '<', '<=', '>', '>=', '=~'
    right: Expr


@dataclass
class InExpr:
    """col in ('a', 'b', 'c')"""
    col: Expr
    values: list[Expr]
    negated: bool = False


@dataclass
class StringOp:
    """has, contains, startswith, endswith, matches regex"""
    col: Expr
    op: str   # 'has', 'contains', 'startswith', 'endswith', 'matches_regex'
    value: str


@dataclass
class NullCheck:
    """isnotnull(col) / isnull(col)"""
    col: Expr
    is_null: bool


@dataclass
class LogicalOp:
    """cond1 and cond2 / cond1 or cond2"""
    left: "BoolExpr"
    op: str  # 'and', 'or'
    right: "BoolExpr"


@dataclass
class Negation:
    """not cond"""
    expr: "BoolExpr"


BoolExpr = Union[Comparison, InExpr, StringOp, NullCheck, LogicalOp, Negation]


# ─── Aggregation Nodes ───────────────────────────────────────────────────────

@dataclass
class AggCount:
    """count() → COUNT(*)"""
    alias: Optional[str] = None


@dataclass
class AggSum:
    """sum(col) → SUM(col)"""
    col: Expr
    alias: Optional[str] = None


@dataclass
class AggAvg:
    """avg(col) → AVG(col)"""
    col: Expr
    alias: Optional[str] = None


@dataclass
class AggMin:
    """min(col) → MIN(col)"""
    col: Expr
    alias: Optional[str] = None


@dataclass
class AggMax:
    """max(col) → MAX(col)"""
    col: Expr
    alias: Optional[str] = None


@dataclass
class AggDCount:
    """dcount(col) → COUNT(DISTINCT col)"""
    col: Expr
    alias: Optional[str] = None


@dataclass
class AggCountIf:
    """countif(cond) → COUNT(CASE WHEN cond THEN 1 END)"""
    condition: BoolExpr
    alias: Optional[str] = None


AggExpr = Union[AggCount, AggSum, AggAvg, AggMin, AggMax, AggDCount, AggCountIf]


# ─── Group By Items ──────────────────────────────────────────────────────────

@dataclass
class BinGroup:
    """by bin(TimeGenerated, 1h)"""
    col: Expr
    amount: int
    unit: str


@dataclass
class PlainGroup:
    """by ServiceName"""
    col: Expr


GroupByItem = Union[BinGroup, PlainGroup]


# ─── Order By ────────────────────────────────────────────────────────────────

@dataclass
class OrderItem:
    """col asc / col desc"""
    col: Expr
    direction: str = "asc"  # 'asc' | 'desc'


# ─── Pipe Operators ──────────────────────────────────────────────────────────

@dataclass
class WhereOp:
    """| where Level == 'Error'"""
    condition: BoolExpr


@dataclass
class ProjectOp:
    """| project Message, Level"""
    columns: list[str]


@dataclass
class SummarizeOp:
    """| summarize count() by ServiceName"""
    aggregations: list[AggExpr]
    group_by: list[GroupByItem] = field(default_factory=list)


@dataclass
class OrderOp:
    """| order by col desc"""
    items: list[OrderItem]


@dataclass
class TakeOp:
    """| take 100"""
    n: int


@dataclass
class DistinctOp:
    """| distinct col1, col2"""
    columns: list[str]     # empty list = DISTINCT *
    star: bool = False


@dataclass
class ExtendOp:
    """| extend alias = expr"""
    assignments: list[tuple[str, Expr]]


@dataclass
class JoinOp:
    """| join kind=inner (RightTable | ...) on key"""
    right: "KQLQuery"
    keys: list[str]
    kind: str = "inner"   # 'inner', 'leftouter', 'rightouter', 'fullouter'


@dataclass
class UnionOp:
    """| union T2, T3"""
    tables: list[str]


@dataclass
class CountOp:
    """| count"""
    pass


PipeOp = Union[
    WhereOp, ProjectOp, SummarizeOp, OrderOp, TakeOp,
    DistinctOp, ExtendOp, JoinOp, UnionOp, CountOp
]


# ─── Top-Level Query ─────────────────────────────────────────────────────────

@dataclass
class LetBinding:
    """let errors = AppLogs | where Level == 'Error';"""
    name: str
    value: "KQLQuery"


@dataclass
class KQLQuery:
    """
    The root AST node. Represents a complete KQL query.

    let_bindings → will become CTEs (WITH ... AS ...)
    table        → the FROM clause
    pipes        → sequential transformations
    """
    table: str
    pipes: list[PipeOp] = field(default_factory=list)
    let_bindings: list[LetBinding] = field(default_factory=list)
