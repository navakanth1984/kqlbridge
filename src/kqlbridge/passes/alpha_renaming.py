from __future__ import annotations
from typing import Any, List, Set, Union, Dict, Optional

from kqlbridge.scoping import ScopeManager, SymbolKind, ScopeType
from kqlbridge.ast_nodes import (
    KQLQuery, LetBinding, ColumnRef, ExtendOp, ProjectOp, WhereOp,
    SummarizeOp, JoinOp, UnionOp, OrderOp, PlainGroup, BinGroup,
    IffExpr, SubqueryInExpr, BinExpr, FuncCall, BinaryOp, Comparison,
    InExpr, StringOp, NullCheck, LogicalOp, Negation, HasAnyExpr,
    OrderItem
)

class AlphaRenamer:
    def __init__(self, scope_manager: ScopeManager):
        self.scope_manager = scope_manager

    def rename_query(self, query: KQLQuery) -> KQLQuery:
        start_scope = self.scope_manager.current_scope

        # 1. Register and rename global let bindings
        for binding in query.let_bindings:
            # Subqueries are evaluated in isolated Subquery scope
            self.scope_manager.push_scope(ScopeType.SUBQUERY)
            self.rename_query(binding.value)
            self.scope_manager.pop_scope()
            
            # Declare the let binding name globally
            self.scope_manager.declare(binding.name, SymbolKind.LET, binding)

        # 2. Sequential pipe transformation
        self.scope_manager.push_scope(ScopeType.PIPELINE)
        new_pipes = []
        for op in query.pipes:
            new_op = self.visit_op(op)
            new_pipes.append(new_op)
        query.pipes = new_pipes

        # Clean up the stack on return to prevent scope leakage
        while self.scope_manager.current_scope != start_scope and self.scope_manager.current_scope.parent is not None:
            self.scope_manager.pop_scope()

        return query

    def visit_op(self, op: Any) -> Any:
        if isinstance(op, WhereOp):
            op.condition = self.visit_expr(op.condition)
            return op
            
        elif isinstance(op, ExtendOp):
            new_assignments = []
            for name, expr in op.assignments:
                # RHS is evaluated in the current scope
                new_expr = self.visit_expr(expr)
                # LHS is declared, potentially shadowed and alpha-renamed
                symbol = self.scope_manager.declare(name, SymbolKind.COLUMN, op)
                new_assignments.append((symbol.unique_name, new_expr))
            op.assignments = new_assignments
            return op
            
        elif isinstance(op, ProjectOp):
            # Resolve RHS expressions
            new_aliases = {}
            if op.aliases:
                for src, alias in op.aliases.items():
                    resolved_src_unique = src
                    symbol = self.scope_manager.lookup(src)
                    if symbol:
                        resolved_src_unique = symbol.unique_name
                    new_aliases[resolved_src_unique] = alias
            
            # Resolve columns
            new_columns = []
            for col in op.columns:
                symbol = self.scope_manager.lookup(col)
                if symbol:
                    new_columns.append(symbol.unique_name)
                else:
                    new_columns.append(col)

            # Purge columns by pushing a new PIPELINE scope
            self.scope_manager.push_scope(ScopeType.PIPELINE)
            
            # Declare newly projected symbols
            if op.aliases:
                for src_uniq, alias in new_aliases.items():
                    self.scope_manager.declare(alias, SymbolKind.COLUMN, op, unique_name=alias)
            for col in op.columns:
                if op.aliases and col in op.aliases.values():
                    continue
                self.scope_manager.declare(col, SymbolKind.COLUMN, op, unique_name=col)

            op.columns = new_columns
            op.aliases = new_aliases if op.aliases else None
            return op
        
        elif isinstance(op, SummarizeOp):
            # 1. Resolve group by items first (in active scope)
            new_group_by = []
            grouping_aliases = set()
            for item in op.group_by:
                if isinstance(item, PlainGroup):
                    new_col = self.visit_expr(item.col)
                    new_group_by.append(PlainGroup(col=new_col))
                    if isinstance(new_col, ColumnRef):
                        grouping_aliases.add(new_col.name)
                elif isinstance(item, BinGroup):
                    new_col = self.visit_expr(item.col)
                    new_group_by.append(BinGroup(col=new_col, amount=item.amount, unit=item.unit))
                    if isinstance(new_col, ColumnRef):
                        grouping_aliases.add(new_col.name)
            
            # 2. Resolve aggregations (in active scope)
            new_aggs = []
            for agg in op.aggregations:
                new_agg = self.visit_agg(agg)
                new_aggs.append(new_agg)
                
                # Check and compute default implicit alias if not defined
                if not getattr(new_agg, "alias", None):
                    from kqlbridge.ast_nodes import (
                        AggCount, AggSum, AggAvg, AggMin, AggMax, AggDCount,
                        AggCountIf, AggSumIf, AggAvgIf, AggMaxIf, AggMinIf,
                        AggDCountIf, AggPercentile, AggMakeList
                    )
                    if isinstance(new_agg, AggCount):
                        new_agg.alias = "count_"
                        new_agg.is_implicit_alias = True
                    elif isinstance(new_agg, AggCountIf):
                        new_agg.alias = "countif_"
                        new_agg.is_implicit_alias = True
                    elif hasattr(new_agg, "col") and new_agg.col is not None:
                        col_name = new_agg.col.name if isinstance(new_agg.col, ColumnRef) else "col"
                        prefix = ""
                        if isinstance(new_agg, AggSum): prefix = "sum_"
                        elif isinstance(new_agg, AggAvg): prefix = "avg_"
                        elif isinstance(new_agg, AggMin): prefix = "min_"
                        elif isinstance(new_agg, AggMax): prefix = "max_"
                        elif isinstance(new_agg, AggDCount): prefix = "dcount_"
                        elif isinstance(new_agg, AggSumIf): prefix = "sumif_"
                        elif isinstance(new_agg, AggAvgIf): prefix = "avgif_"
                        elif isinstance(new_agg, AggMaxIf): prefix = "maxif_"
                        elif isinstance(new_agg, AggMinIf): prefix = "minif_"
                        elif isinstance(new_agg, AggDCountIf): prefix = "dcountif_"
                        elif isinstance(new_agg, AggPercentile): prefix = "percentile_"
                        elif isinstance(new_agg, AggMakeList): prefix = "make_list_"
                        if prefix:
                            new_agg.alias = f"{prefix}{col_name}"
                            new_agg.is_implicit_alias = True
                
                if new_agg.alias:
                    grouping_aliases.add(new_agg.alias)

            # Summarize acts as an AGGREGATE "Schema Guillotine" boundary
            self.scope_manager.push_scope(ScopeType.AGGREGATE, grouping_keys=grouping_aliases)

            # Declare summarize grouping and aggregation columns in aggregate scope
            for item in op.group_by:
                if isinstance(item, PlainGroup) and isinstance(item.col, ColumnRef):
                    self.scope_manager.declare(item.col.name, SymbolKind.COLUMN, op, unique_name=item.col.name)
                elif isinstance(item, BinGroup) and isinstance(item.col, ColumnRef):
                    self.scope_manager.declare(item.col.name, SymbolKind.COLUMN, op, unique_name=item.col.name)

            for agg in op.aggregations:
                if agg.alias:
                    self.scope_manager.declare(agg.alias, SymbolKind.AGGREGATE, op, unique_name=agg.alias)

            op.group_by = new_group_by
            op.aggregations = new_aggs
            return op
        
        elif isinstance(op, JoinOp):
            self.scope_manager.push_scope(ScopeType.SUBQUERY)
            self.rename_query(op.right)
            self.scope_manager.pop_scope()
            return op

        elif isinstance(op, OrderOp):
            for item in op.items:
                item.col = self.visit_expr(item.col)
            return op

        return op

    def visit_expr(self, expr: Any) -> Any:
        if isinstance(expr, ColumnRef):
            # Resolve the reference, raising UndefinedSymbolError if not declared
            symbol = self.scope_manager.resolve(expr.name)
            return ColumnRef(name=symbol.unique_name)
        elif isinstance(expr, IffExpr):
            expr.condition = self.visit_expr(expr.condition)
            expr.true_val = self.visit_expr(expr.true_val)
            expr.false_val = self.visit_expr(expr.false_val)
        elif isinstance(expr, SubqueryInExpr):
            expr.col = self.visit_expr(expr.col)
            self.scope_manager.push_scope(ScopeType.SUBQUERY)
            self.rename_query(expr.subquery)
            self.scope_manager.pop_scope()
        elif isinstance(expr, BinExpr):
            expr.col = self.visit_expr(expr.col)
        elif isinstance(expr, FuncCall):
            expr.args = [self.visit_expr(arg) for arg in expr.args]
        elif isinstance(expr, BinaryOp):
            expr.left = self.visit_expr(expr.left)
            expr.right = self.visit_expr(expr.right)
        elif isinstance(expr, Comparison):
            expr.left = self.visit_expr(expr.left)
            expr.right = self.visit_expr(expr.right)
        elif isinstance(expr, InExpr):
            expr.col = self.visit_expr(expr.col)
            expr.values = [self.visit_expr(v) for v in expr.values]
        elif isinstance(expr, StringOp):
            expr.col = self.visit_expr(expr.col)
        elif isinstance(expr, NullCheck):
            expr.col = self.visit_expr(expr.col)
        elif isinstance(expr, LogicalOp):
            expr.left = self.visit_expr(expr.left)
            expr.right = self.visit_expr(expr.right)
        elif isinstance(expr, Negation):
            expr.expr = self.visit_expr(expr.expr)
        elif isinstance(expr, HasAnyExpr):
            expr.col = self.visit_expr(expr.col)
            expr.values = [self.visit_expr(v) for v in expr.values]
        return expr

    def visit_agg(self, agg: Any) -> Any:
        if hasattr(agg, "col") and agg.col is not None:
            agg.col = self.visit_expr(agg.col)
        if hasattr(agg, "condition") and agg.condition is not None:
            agg.condition = self.visit_expr(agg.condition)
        return agg
