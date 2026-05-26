from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

class ScopeType(Enum):
    GLOBAL = "GLOBAL"          # Outer let bindings
    PIPELINE = "PIPELINE"      # Sequential pipe operators (extend, project)
    SUBQUERY = "SUBQUERY"      # Relational subquery boundaries (joins, unions)
    AGGREGATE = "AGGREGATE"    # Aggregation boundary scopes (summarize)

class SymbolKind(Enum):
    LET = "LET"                # Explicit scalar/tabular let declarations
    COLUMN = "COLUMN"          # Transient physical or generated columns
    AGGREGATE = "AGGREGATE"    # Aggregate metrics (e.g., count(), sum())
    PARAMETER = "PARAMETER"    # Query/engine parameters
    FUNCTION = "FUNCTION"      # Native or user-defined function mappings

class FunctionPurity(Enum):
    PURE = "PURE"                          # Fully foldable statically
    CONTEXT_DEPENDENT = "CONTEXT_DEPENDENT"  # Bypassed (e.g., now(), ago())
    NON_DETERMINISTIC = "NON_DETERMINISTIC"  # Protected (e.g., rand())

class UndefinedSymbolError(ValueError):
    """Raised when KQL query references an undeclared symbol."""
    pass

@dataclass(slots=True)
class SymbolInfo:
    symbol_id: int             # Immutable, auto-incrementing symbol identity
    name: str                  # Original identifier
    unique_name: str           # Compiler-generated non-colliding name
    symbol_kind: SymbolKind
    scope_depth: int
    origin_scope: Optional[SymbolTable] = None
    origin_node: Any = None    # AST node where the symbol was defined
    derived_from: List[int] = field(default_factory=list) # Lineage symbol ID tracking

    @property
    def id(self) -> int:
        return self.symbol_id


@dataclass(slots=True)
class ScopeAnalysisResult:
    scopes_created: int = 0
    symbols_declared: int = 0
    symbols_renamed: int = 0
    unresolved_symbols: int = 0

class SymbolTable:
    def __init__(
        self,
        parent: Optional[SymbolTable] = None,
        scope_type: ScopeType = ScopeType.PIPELINE,
        grouping_keys: Optional[Set[str]] = None,
        is_schema_truncated: bool = False
    ):
        self.parent = parent
        self.scope_type = scope_type
        self.symbols: Dict[str, SymbolInfo] = {}
        self.is_isolation_boundary: bool = (scope_type == ScopeType.AGGREGATE or scope_type == ScopeType.SUBQUERY)
        self.grouping_keys: Set[str] = grouping_keys if grouping_keys is not None else set()
        self.is_schema_truncated: bool = is_schema_truncated or (scope_type == ScopeType.AGGREGATE)

    def declare(
        self,
        name: str,
        symbol_kind: SymbolKind,
        origin_node: Any,
        depth: int,
        symbol_id: int,
        unique_name: Optional[str] = None
    ) -> SymbolInfo:
        # Check if we collide with any ancestor scope declarations
        collides = False
        ancestor = self.parent
        while ancestor:
            if name in ancestor.symbols:
                collides = True
                break
            ancestor = ancestor.parent

        if unique_name is None:
            if collides:
                unique_name = f"__kqlbridge_sym_{symbol_id}"
            else:
                unique_name = name

        symbol = SymbolInfo(
            symbol_id=symbol_id,
            name=name,
            unique_name=unique_name,
            symbol_kind=symbol_kind,
            scope_depth=depth,
            origin_scope=self,
            origin_node=origin_node
        )
        self.symbols[name] = symbol
        return symbol

    def lookup_local(self, name: str) -> Optional[SymbolInfo]:
        return self.symbols.get(name)

    def lookup_id(self, symbol_id: int) -> Optional[SymbolInfo]:
        # Search locally
        for sym in self.symbols.values():
            if sym.symbol_id == symbol_id:
                return sym
        # Search parent
        if self.parent:
            return self.parent.lookup_id(symbol_id)
        return None

    def all_symbols(self) -> List[SymbolInfo]:
        """Recursively gathers all unique symbols from this scope and ancestors."""
        collected = {}
        curr = self
        while curr is not None:
            for name, sym in curr.symbols.items():
                if sym.symbol_id not in collected:
                    collected[sym.symbol_id] = sym
            curr = curr.parent
        return list(collected.values())



class ScopeManager:
    def __init__(self):
        self.global_scope = SymbolTable(scope_type=ScopeType.GLOBAL)
        self.current_scope = self.global_scope
        self.depth = 0
        self._symbol_id_counter = 0
        self.analysis_result = ScopeAnalysisResult()
        self.analysis_result.scopes_created = 1

    def _next_symbol_id(self) -> int:
        self._symbol_id_counter += 1
        return self._symbol_id_counter

    def push_scope(self, scope_type: ScopeType, grouping_keys: Optional[Set[str]] = None, is_schema_truncated: bool = False):
        self.depth += 1
        new_scope = SymbolTable(
            parent=self.current_scope,
            scope_type=scope_type,
            grouping_keys=grouping_keys,
            is_schema_truncated=is_schema_truncated
        )
        self.current_scope = new_scope
        self.analysis_result.scopes_created += 1

    def pop_scope(self):
        if self.current_scope.parent is not None:
            self.current_scope = self.current_scope.parent
            self.depth -= 1

    def declare(
        self,
        name: str,
        symbol_kind: SymbolKind,
        origin_node: Any = None,
        unique_name: Optional[str] = None
    ) -> SymbolInfo:
        symbol_id = self._next_symbol_id()
        symbol = self.current_scope.declare(
            name=name,
            symbol_kind=symbol_kind,
            origin_node=origin_node,
            depth=self.depth,
            symbol_id=symbol_id,
            unique_name=unique_name
        )
        self.analysis_result.symbols_declared += 1
        if symbol.unique_name != symbol.name:
            self.analysis_result.symbols_renamed += 1
        return symbol

    def lookup(self, name: str) -> Optional[SymbolInfo]:
        """Looks up a symbol recursively but respects isolation boundaries (guillotine / subquery)."""
        # 1. Normal lookup respecting boundaries
        curr = self.current_scope
        symbol = None
        while curr is not None:
            symbol = curr.lookup_local(name)
            if symbol is not None:
                if symbol.symbol_kind == SymbolKind.COLUMN and self._crosses_subquery_boundary(curr):
                    curr = curr.parent
                    continue
                break
            
            if curr.scope_type == ScopeType.AGGREGATE and name not in curr.grouping_keys:
                ancestor = curr.parent
                found_non_col = False
                while ancestor:
                    ans_symbol = ancestor.lookup_local(name)
                    if ans_symbol and ans_symbol.symbol_kind != SymbolKind.COLUMN:
                        found_non_col = True
                        break
                    ancestor = ancestor.parent
                if not found_non_col:
                    break
            curr = curr.parent

        if symbol is not None:
            return symbol

        # 2. Auto-declare new implicit physical COLUMN in CURRENT scope
        # KQL is dynamic; we always allow auto-declaring columns in the active pipeline
        # to handle joins/subqueries that might introduce them.
        symbol = self.current_scope.declare(
            name=name,
            symbol_kind=SymbolKind.COLUMN,
            origin_node=None,
            depth=self.depth,
            symbol_id=self._next_symbol_id(),
            unique_name=name
        )
        self.analysis_result.symbols_declared += 1
        return symbol

    def resolve(self, name: str) -> SymbolInfo:
        """Resolves a symbol name or raises UndefinedSymbolError if it is undeclared."""
        symbol = self.lookup(name)
        if symbol is None:
            self.analysis_result.unresolved_symbols += 1
            raise UndefinedSymbolError(f"Undefined symbol: '{name}'")
        return symbol

    def _crosses_subquery_boundary(self, target_scope: SymbolTable) -> bool:
        curr = self.current_scope
        while curr is not None and curr != target_scope:
            if curr.scope_type == ScopeType.SUBQUERY:
                return True
            curr = curr.parent
        return False

    def _is_schema_truncated(self) -> bool:
        curr = self.current_scope
        while curr is not None:
            if curr.is_schema_truncated:
                return True
            if curr.scope_type == ScopeType.SUBQUERY:
                break
            curr = curr.parent
        return False
