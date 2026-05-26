from typing import Any, Dict, List, Optional, Set
from ..ast_nodes import (
    KQLQuery, ColumnRef, ExtendOp, ProjectOp, WhereOp,
    SummarizeOp, JoinOp, UnionOp, OrderOp, PlainGroup, BinGroup,
    IffExpr, SubqueryInExpr, BinExpr, FuncCall, BinaryOp, Comparison,
    InExpr, StringOp, NullCheck, LogicalOp, Negation, HasAnyExpr,
    AggCount, AggSum, AggAvg, AggMin, AggMax, AggDCount, AggCountIf,
    AggSumIf, AggAvgIf, AggMaxIf, AggMinIf, AggDCountIf, AggPercentile, AggMakeList,
    TakeOp, DistinctOp, CountOp, SerializeOp, DatetimeLit, AgoExpr
)
from ..scoping import ScopeManager, SymbolKind, ScopeType, SymbolTable, SymbolInfo
from .nodes import (
    SemanticIRNode,
    SemanticExpression,
    SemanticColumnRef,
    SemanticLiteral,
    SemanticComparison,
    SemanticLogicalOp,
    SemanticFunctionCall,
    SemanticSubquery,
    SemanticQuery,
    SemanticFilter,
    ProjectionItem,
    SemanticProjection,
    AggregateItem,
    SemanticAggregate,
    SemanticJoin,
    SemanticUnion,
)

def collect_expression_symbol_ids(expr: SemanticExpression) -> List[int]:
    """Helper to collect and deduplicate all symbol IDs in a Semantic Expression."""
    ids = []
    if isinstance(expr, SemanticColumnRef):
        ids.append(expr.symbol_id)
    elif isinstance(expr, SemanticComparison):
        ids.extend(collect_expression_symbol_ids(expr.left))
        ids.extend(collect_expression_symbol_ids(expr.right))
    elif isinstance(expr, SemanticLogicalOp):
        for e in expr.expressions:
            ids.extend(collect_expression_symbol_ids(e))
    elif isinstance(expr, SemanticFunctionCall):
        for arg in expr.arguments:
            ids.extend(collect_expression_symbol_ids(arg))
    elif isinstance(expr, SemanticSubquery):
        # We can scan the subquery steps if necessary, but keep it isolated in Phase 2A
        pass
    return sorted(list(set(ids)))

def get_visible_column_symbols(symbol_table: SymbolTable) -> List[SymbolInfo]:
    """Traverses symbol tables upwards to collect all currently active, visible column symbols."""
    visible = {}
    curr = symbol_table
    crossed_subquery = False
    schema_truncated = False
    
    while curr is not None:
        if curr.is_schema_truncated:
            schema_truncated = True
        
        for name, sym in curr.symbols.items():
            if sym.symbol_kind == SymbolKind.COLUMN:
                if schema_truncated:
                    # Column lookups are blocked post-aggregate unless they are grouping keys
                    continue
                if crossed_subquery:
                    # Subquery boundaries isolate parent column lookup
                    continue
                
                if name not in visible:
                    visible[name] = sym
                    
        if curr.scope_type == ScopeType.SUBQUERY:
            crossed_subquery = True
        curr = curr.parent
        
    return list(visible.values())

class ASTToIRTransformer:
    def __init__(self, initial_scope: Optional[SymbolTable] = None):
        self.scope_manager = ScopeManager()
        if initial_scope:
            self.scope_manager.global_scope = initial_scope
            self.scope_manager.current_scope = initial_scope
        self.pipeline_state: Dict[str, Any] = {}

    def visit_query(self, query: KQLQuery) -> SemanticQuery:
        # Save outer pipeline state for recursive/nested queries (e.g. joins, unions, let CTEs)
        outer_pipeline_state = self.pipeline_state
        self.pipeline_state = {}

        outer_ctes = getattr(self, "_current_ctes", None)
        ctes: Dict[str, SemanticQuery] = {}
        self._current_ctes = ctes
        scalar_bindings: Dict[str, Any] = {}
        
        # 1. Transform CTE bindings recursively
        for binding in query.let_bindings:
            # Detect scalar let bindings: table == '__scalar__' with scalar_expr.
            # These are inlined, NOT emitted as CTEs.
            if (getattr(binding.value, 'table', None) == '__scalar__' 
                    and hasattr(binding.value, 'scalar_expr')):
                # Store the scalar expression for inline substitution
                scalar_expr_ir = self.visit_expr(binding.value.scalar_expr)
                scalar_bindings[binding.name] = scalar_expr_ir
                self.scope_manager.declare(binding.name, SymbolKind.LET, binding, unique_name=binding.name)
                continue
                
            self.scope_manager.push_scope(ScopeType.SUBQUERY)
            cte_query = self.visit_query(binding.value)
            self.scope_manager.pop_scope()
            
            # Register in scoping manager
            self.scope_manager.declare(binding.name, SymbolKind.LET, binding, unique_name=binding.name)
            ctes[binding.name] = cte_query
            
        # 2. Sequential pipeline transformations
        self.scope_manager.push_scope(ScopeType.PIPELINE)
        steps: List[SemanticIRNode] = []
        for op in query.pipes:
            step = self.visit_op(op)
            if step is not None:
                steps.append(step)
                
        res_pipeline_state = self.pipeline_state
        self.pipeline_state = outer_pipeline_state

        sq = SemanticQuery(
            source=query.table,
            steps=steps,
            ctes=ctes,
            symbol_table=self.scope_manager.current_scope,
            pipeline_state=res_pipeline_state,
            query_id=id(query),
            scalar_bindings=scalar_bindings
        )
        self._current_ctes = outer_ctes
        return sq

    def visit_op(self, op: Any) -> Optional[SemanticIRNode]:
        if isinstance(op, WhereOp):
            pred = self.visit_expr(op.condition)
            return SemanticFilter(predicate=pred, origin_node=op)
            
        elif isinstance(op, ExtendOp):
            # Pull visible column symbols *before* declaring the new assignments
            visible_cols = get_visible_column_symbols(self.scope_manager.current_scope)
            proj_items: Dict[str, ProjectionItem] = {}
            
            # Map existing columns to projections
            for sym in visible_cols:
                proj_items[sym.unique_name] = ProjectionItem(
                    alias=sym.unique_name,
                    expression=SemanticColumnRef(name=sym.name, symbol_id=sym.symbol_id),
                    symbol_id=sym.symbol_id,
                    derived_from=[sym.symbol_id],
                    origin_node=None
                )
                
            # Process and overwrite with newly assigned columns
            for name, expr in op.assignments:
                expr_node = self.visit_expr(expr)
                sym = self.scope_manager.declare(name, SymbolKind.COLUMN, op, unique_name=name)
                derived = collect_expression_symbol_ids(expr_node)
                
                proj_items[name] = ProjectionItem(
                    alias=name,
                    expression=expr_node,
                    symbol_id=sym.symbol_id,
                    derived_from=derived,
                    origin_node=op
                )
                
            return SemanticProjection(items=list(proj_items.values()), is_extend_only=True)
            
        elif isinstance(op, ProjectOp):
            # Purge columns by pushing a new PIPELINE scope
            self.scope_manager.push_scope(ScopeType.PIPELINE)
            items: List[ProjectionItem] = []
            
            # Project aliased columns
            if op.aliases:
                for src, alias in op.aliases.items():
                    sym = self.scope_manager.declare(alias, SymbolKind.COLUMN, op, unique_name=alias)
                    src_sym = self.scope_manager.lookup(src)
                    src_id = src_sym.symbol_id if src_sym else 0
                    
                    items.append(ProjectionItem(
                         alias=alias,
                         expression=SemanticColumnRef(name=src, symbol_id=src_id),
                         symbol_id=sym.symbol_id,
                         derived_from=[src_id] if src_id else [],
                         origin_node=op
                    ))
                    
            # Project plain columns
            for col in op.columns:
                if op.aliases and col in op.aliases:
                    continue
                sym = self.scope_manager.declare(col, SymbolKind.COLUMN, op, unique_name=col)
                items.append(ProjectionItem(
                    alias=col,
                    expression=SemanticColumnRef(name=col, symbol_id=sym.symbol_id),
                    symbol_id=sym.symbol_id,
                    derived_from=[sym.symbol_id],
                    origin_node=op
                ))
                
            return SemanticProjection(items=items, is_extend_only=False)
            
        elif isinstance(op, SummarizeOp):
            grouping_keys: Set[str] = set()
            group_by_items: List[ProjectionItem] = []
            
            # 1. Process groupings in active scope before summarize boundary
            for gb in op.group_by:
                if isinstance(gb, PlainGroup):
                    gb_expr = self.visit_expr(gb.col)
                    derived = collect_expression_symbol_ids(gb_expr)
                    alias = gb_expr.name if isinstance(gb_expr, SemanticColumnRef) else "key"
                    
                    grouping_keys.add(alias)
                    group_by_items.append(ProjectionItem(
                        alias=alias,
                        expression=gb_expr,
                        symbol_id=gb_expr.symbol_id if isinstance(gb_expr, SemanticColumnRef) else 0,
                        derived_from=derived,
                        origin_node=gb
                    ))
                elif isinstance(gb, BinGroup):
                    gb_expr = self.visit_expr(gb.col)
                    derived = collect_expression_symbol_ids(gb_expr)
                    alias = gb_expr.name if isinstance(gb_expr, SemanticColumnRef) else "bin_key"
                    
                    grouping_keys.add(alias)
                    group_by_items.append(ProjectionItem(
                        alias=alias,
                        expression=SemanticFunctionCall(
                            name="bin",
                            arguments=[gb_expr, SemanticLiteral(value=f"{gb.amount}{gb.unit}")]
                        ),
                        symbol_id=0,
                        derived_from=derived,
                        origin_node=gb
                    ))
                    
            # 2. Push summarize aggregate isolation scope
            self.scope_manager.push_scope(ScopeType.AGGREGATE, grouping_keys=grouping_keys)
            
            # Declare the grouping items in the new aggregate scope
            for item in group_by_items:
                sym = self.scope_manager.declare(item.alias, SymbolKind.COLUMN, op, unique_name=item.alias)
                item.symbol_id = sym.symbol_id
                
            aggregations: List[AggregateItem] = []
            for agg in op.aggregations:
                args = []
                func_name = ""
                is_distinct = False
                
                if isinstance(agg, AggCount):
                    func_name = "count"
                elif isinstance(agg, AggSum):
                    func_name = "sum"
                    args = [self.visit_expr(agg.col)]
                elif isinstance(agg, AggAvg):
                    func_name = "avg"
                    args = [self.visit_expr(agg.col)]
                elif isinstance(agg, AggMin):
                    func_name = "min"
                    args = [self.visit_expr(agg.col)]
                elif isinstance(agg, AggMax):
                    func_name = "max"
                    args = [self.visit_expr(agg.col)]
                elif isinstance(agg, AggDCount):
                    func_name = "dcount"
                    args = [self.visit_expr(agg.col)]
                    is_distinct = True
                elif isinstance(agg, AggCountIf):
                    func_name = "countif"
                    args = [self.visit_expr(agg.condition)]
                elif isinstance(agg, AggSumIf):
                    func_name = "sumif"
                    args = [self.visit_expr(agg.col), self.visit_expr(agg.condition)]
                elif isinstance(agg, AggAvgIf):
                    func_name = "avgif"
                    args = [self.visit_expr(agg.col), self.visit_expr(agg.condition)]
                elif isinstance(agg, AggMaxIf):
                    func_name = "maxif"
                    args = [self.visit_expr(agg.col), self.visit_expr(agg.condition)]
                elif isinstance(agg, AggMinIf):
                    func_name = "minif"
                    args = [self.visit_expr(agg.col), self.visit_expr(agg.condition)]
                elif isinstance(agg, AggDCountIf):
                    func_name = "dcountif"
                    args = [self.visit_expr(agg.col), self.visit_expr(agg.condition)]
                    is_distinct = True
                elif isinstance(agg, AggPercentile):
                    func_name = "percentile"
                    args = [self.visit_expr(agg.col), self.visit_expr(agg.percentile)]
                elif isinstance(agg, AggMakeList):
                    func_name = "make_list"
                    args = [self.visit_expr(agg.col)]
                    
                alias = agg.alias if getattr(agg, "alias", None) else f"{func_name}_"
                sym = self.scope_manager.declare(alias, SymbolKind.COLUMN, op, unique_name=alias)
                
                derived = []
                for arg in args:
                    derived.extend(collect_expression_symbol_ids(arg))
                derived = sorted(list(set(derived)))
                
                aggregations.append(AggregateItem(
                    alias=alias,
                    function_name=func_name,
                    arguments=args,
                    symbol_id=sym.symbol_id,
                    derived_from=derived,
                    origin_node=agg,
                    is_distinct=is_distinct
                ))
                
            return SemanticAggregate(aggregations=aggregations, group_by=group_by_items)
            
        elif isinstance(op, JoinOp):
            right_query = self.visit_query(op.right)
            from .nodes import SemanticJoinCondition
            conditions = []
            for key in op.keys:
                left_sym = self.scope_manager.lookup(key)
                left_sid = left_sym.symbol_id if left_sym else 0
                
                right_sym = None
                if right_query.symbol_table:
                    curr_tbl = right_query.symbol_table
                    while curr_tbl:
                        right_sym = curr_tbl.lookup_local(key)
                        if right_sym:
                            break
                        curr_tbl = curr_tbl.parent
                right_sid = right_sym.symbol_id if right_sym else 0
                
                conditions.append(SemanticJoinCondition(
                    left_symbol_id=left_sid,
                    right_symbol_id=right_sid,
                    left_col=key,
                    right_col=key,
                    operator="=="
                ))
                
            right_alias = op.right.table
            
            # In standard mode, we do NOT hoist right-side join subqueries to CTEs.
            # We keep them inline (just like legacy SparkSQLGenerator) to ensure perfect 
            # backward compatibility, identical SQL output format, and 100% convergence.
            # Thus, we do not register right_query into the CTE registry here.
                
            return SemanticJoin(
                right_query=right_query,
                kind=op.kind,
                conditions=conditions,
                on_keys=op.keys
            )
            
        elif isinstance(op, UnionOp):
            transformed_subqueries = {}
            if op.subqueries:
                for k, v in op.subqueries.items():
                    transformed_subqueries[k] = self.visit_query(v)

            inputs = []
            for item in op.tables:
                if op.subqueries and item in op.subqueries:
                    inputs.append(transformed_subqueries[item])
                else:
                    inputs.append(SemanticQuery(
                        source=item,
                        steps=[],
                        ctes={},
                        symbol_table=SymbolTable(scope_type=ScopeType.PIPELINE)
                    ))

            # Alignment logic
            has_projection = False
            for branch in inputs:
                if branch.steps and any(isinstance(s, SemanticProjection) for s in branch.steps):
                    has_projection = True
            
            mappings = []
            if has_projection:
                primary_cols = get_visible_column_symbols(self.scope_manager.current_scope)
                branch_cols_list = []
                for branch in inputs:
                    b_cols = []
                    for s in reversed(branch.steps):
                        if isinstance(s, SemanticProjection):
                            b_cols = s.items
                            break
                        elif isinstance(s, SemanticAggregate):
                            b_cols = s.aggregations + s.group_by
                            break
                    branch_cols_list.append(b_cols)
                
                all_aliases = []
                seen_aliases = set()
                
                for col in primary_cols:
                    if col.name not in seen_aliases:
                        seen_aliases.add(col.name)
                        all_aliases.append(col.name)
                
                for b_cols in branch_cols_list:
                    for item in b_cols:
                        if item.alias not in seen_aliases:
                            seen_aliases.add(item.alias)
                            all_aliases.append(item.alias)
                
                from .nodes import UnionColumnMapping
                for alias in all_aliases:
                    source_mappings = {}
                    for branch_idx, b_cols in enumerate(branch_cols_list):
                        match_id = None
                        for item in b_cols:
                            if item.alias == alias:
                                match_id = item.symbol_id
                                break
                        source_mappings[branch_idx] = match_id
                    
                    mappings.append(UnionColumnMapping(
                        output_alias=alias,
                        source_mappings=source_mappings,
                        is_nullable=any(sid is None for sid in source_mappings.values())
                    ))

            return SemanticUnion(
                tables=op.tables,
                inputs=inputs,
                mappings=mappings,
                subqueries=transformed_subqueries
            )
            
        elif isinstance(op, OrderOp):
            self.pipeline_state["order_by"] = [
                {"column": item.col.name if isinstance(item.col, ColumnRef) else str(item.col), "direction": item.direction}
                for item in op.items
            ]
            return None
            
        elif isinstance(op, TakeOp):
            self.pipeline_state["limit"] = op.n
            return None
            
        elif isinstance(op, DistinctOp):
            self.pipeline_state["distinct"] = {"columns": op.columns, "star": op.star}
            return None
            
        elif isinstance(op, CountOp):
            self.pipeline_state["count"] = True
            return None
            
        elif isinstance(op, SerializeOp):
            self.pipeline_state["serialize"] = True
            return None
            
        return None

    def visit_expr(self, expr: Any) -> SemanticExpression:
        if isinstance(expr, ColumnRef):
            sym = self.scope_manager.lookup(expr.name)
            sym_id = sym.symbol_id if sym else 0
            name = sym.unique_name if sym else expr.name
            return SemanticColumnRef(name=name, symbol_id=sym_id)
            
        elif hasattr(expr, "value") and not isinstance(expr, (PlainGroup, BinGroup, SubqueryInExpr, StringOp)):
            return SemanticLiteral(value=expr.value)
            
        elif isinstance(expr, DatetimeLit):
            return SemanticLiteral(value=expr.raw)
            
        elif isinstance(expr, Comparison):
            return SemanticComparison(
                left=self.visit_expr(expr.left),
                op=expr.op,
                right=self.visit_expr(expr.right)
            )
            
        elif isinstance(expr, LogicalOp):
            return SemanticLogicalOp(
                op=expr.op,
                expressions=[self.visit_expr(expr.left), self.visit_expr(expr.right)]
            )
            
        elif isinstance(expr, Negation):
            return SemanticLogicalOp(
                op="not",
                expressions=[self.visit_expr(expr.expr)]
            )
            
        elif isinstance(expr, FuncCall):
            return SemanticFunctionCall(
                name=expr.name,
                arguments=[self.visit_expr(arg) for arg in expr.args]
            )
            
        elif isinstance(expr, BinaryOp):
            return SemanticFunctionCall(
                name=expr.op,
                arguments=[self.visit_expr(expr.left), self.visit_expr(expr.right)]
            )
            
        elif isinstance(expr, BinExpr):
            return SemanticFunctionCall(
                name="bin",
                arguments=[
                    self.visit_expr(expr.col),
                    SemanticLiteral(value=f"{expr.amount}{expr.unit}")
                ]
            )
            
        elif isinstance(expr, AgoExpr):
            return SemanticFunctionCall(
                name="ago",
                arguments=[SemanticLiteral(value=f"{expr.amount}{expr.unit}")]
            )
            
        elif isinstance(expr, IffExpr):
            return SemanticFunctionCall(
                name="iff",
                arguments=[
                    self.visit_expr(expr.condition),
                    self.visit_expr(expr.true_val),
                    self.visit_expr(expr.false_val)
                ]
            )
            
        elif isinstance(expr, SubqueryInExpr):
            cte_query = self.visit_query(expr.subquery)
            subquery_node = SemanticSubquery(query=cte_query)
            name = "not_in" if expr.negated else "in"
            if getattr(expr, "case_insensitive", False):
                name += "_case_insensitive"
            return SemanticFunctionCall(
                name=name,
                arguments=[self.visit_expr(expr.col), subquery_node]
            )
            
        elif isinstance(expr, InExpr):
            args = [self.visit_expr(expr.col)] + [self.visit_expr(v) for v in expr.values]
            name = "not_in" if expr.negated else "in"
            if expr.case_insensitive:
                name += "_case_insensitive"
            return SemanticFunctionCall(name=name, arguments=args)
            
        elif isinstance(expr, StringOp):
            return SemanticFunctionCall(
                name=expr.op,
                arguments=[self.visit_expr(expr.col), SemanticLiteral(value=expr.value)]
            )
            
        elif isinstance(expr, NullCheck):
            name = "isnull" if expr.is_null else "isnotnull"
            return SemanticFunctionCall(
                name=name,
                arguments=[self.visit_expr(expr.col)]
            )
            
        elif isinstance(expr, HasAnyExpr):
            args = [self.visit_expr(expr.col)] + [self.visit_expr(v) for v in expr.values]
            return SemanticFunctionCall(name="has_any", arguments=args)
            
        # Fallback to literal representation if unknown scalar node type
        return SemanticLiteral(value=str(expr))

def to_semantic_ir(query: KQLQuery, symbol_table: Optional[SymbolTable] = None, validate: bool = False) -> SemanticQuery:
    """Entry point to compile a fully scoped/folded AST to Semantic IR nodes."""
    transformer = ASTToIRTransformer(symbol_table)
    res = transformer.visit_query(query)
    if validate:
        from .validator import validate_ir, IRValidationError
        vr = validate_ir(res)
        if not vr.is_valid:
            raise IRValidationError(vr)
    return res
