from __future__ import annotations
from typing import Any, Dict
import copy

from kqlbridge.ast_nodes import (
    KQLQuery, ColumnRef, ExtendOp, ProjectOp, WhereOp,
    SummarizeOp, JoinOp, OrderOp, PlainGroup, BinGroup,
    IffExpr, SubqueryInExpr, BinExpr, FuncCall, BinaryOp, Comparison,
    InExpr, StringOp, NullCheck, LogicalOp, Negation, HasAnyExpr,
    IntLit, FloatLit, BoolLit, StringLit, DatetimeLit
)
from kqlbridge.scoping import ScopeManager, ScopeType

class ConstantFolder:
    def __init__(self, scope_manager: ScopeManager):
        self.scope_manager = scope_manager
        # Cache of folded LET variable values by their unique_name
        self.let_values: Dict[str, Any] = {}

    def fold_query(self, query: KQLQuery) -> KQLQuery:
        start_scope = self.scope_manager.current_scope

        # First, process let bindings
        new_let_bindings = []
        for binding in query.let_bindings:
            # Propagate let binding subqueries in isolated Scope Manager
            self.scope_manager.push_scope(ScopeType.SUBQUERY)
            binding.value = self.fold_query(binding.value)
            self.scope_manager.pop_scope()

            # If it's a scalar let binding, fold it
            if binding.value.table == "__scalar__" and hasattr(binding.value, "scalar_expr"):
                folded_expr = self.fold_expr(binding.value.scalar_expr)
                binding.value.scalar_expr = folded_expr
                
                # Check if it is a constant literal
                if isinstance(folded_expr, (IntLit, FloatLit, BoolLit, StringLit, DatetimeLit)):
                    # Cache the folded value using the unique_name of the symbol
                    symbol = self.scope_manager.lookup(binding.name)
                    if symbol:
                        self.let_values[symbol.unique_name] = folded_expr

            new_let_bindings.append(binding)
        query.let_bindings = new_let_bindings

        # Fold sequential pipe transformations
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
            op.condition = self.fold_expr(op.condition)
            return op
            
        elif isinstance(op, ExtendOp):
            new_assignments = []
            for name, expr in op.assignments:
                # Fold the RHS expression
                new_expr = self.fold_expr(expr)
                new_assignments.append((name, new_expr))
            op.assignments = new_assignments
            return op
            
        elif isinstance(op, ProjectOp):
            return op
        
        elif isinstance(op, SummarizeOp):
            new_group_by = []
            for item in op.group_by:
                if isinstance(item, PlainGroup):
                    item.col = self.fold_expr(item.col)
                elif isinstance(item, BinGroup):
                    item.col = self.fold_expr(item.col)
                new_group_by.append(item)
            
            new_aggs = []
            for agg in op.aggregations:
                if hasattr(agg, "col") and agg.col is not None:
                    agg.col = self.fold_expr(agg.col)
                if hasattr(agg, "condition") and agg.condition is not None:
                    agg.condition = self.fold_expr(agg.condition)
                new_aggs.append(agg)

            op.group_by = new_group_by
            op.aggregations = new_aggs
            return op
        
        elif isinstance(op, JoinOp):
            self.scope_manager.push_scope(ScopeType.SUBQUERY)
            op.right = self.fold_query(op.right)
            self.scope_manager.pop_scope()
            return op

        elif isinstance(op, OrderOp):
            for item in op.items:
                item.col = self.fold_expr(item.col)
            return op

        return op

    def fold_expr(self, expr: Any) -> Any:
        if isinstance(expr, ColumnRef):
            # If it references a static folded let-binding, substitute it!
            symbol = self.scope_manager.lookup(expr.name)
            if symbol and symbol.unique_name in self.let_values:
                folded = copy.deepcopy(self.let_values[symbol.unique_name])
                # Ensure the folded literal preserves lineage metadata!
                if not hasattr(folded, "metadata") or folded.metadata is None:
                    folded.metadata = {}
                folded.metadata.update({
                    "symbol_id": symbol.symbol_id,
                    "name": symbol.name,
                    "unique_name": symbol.unique_name,
                    "symbol_kind": symbol.symbol_kind.value,
                    "derived_from": symbol.derived_from
                })
                return folded
            return expr

        elif isinstance(expr, BinaryOp):
            expr.left = self.fold_expr(expr.left)
            expr.right = self.fold_expr(expr.right)
            if isinstance(expr.left, (IntLit, FloatLit)) and isinstance(expr.right, (IntLit, FloatLit)):
                lval = expr.left.value
                rval = expr.right.value
                val = None
                try:
                    if expr.op == "+":
                        val = lval + rval
                    elif expr.op == "-":
                        val = lval - rval
                    elif expr.op == "*":
                        val = lval * rval
                    elif expr.op == "/":
                        if rval != 0:
                            val = lval / rval
                    elif expr.op == "%":
                        if rval != 0:
                            val = lval % rval
                except Exception:
                    pass
                
                if val is not None:
                    if isinstance(val, int):
                        return IntLit(value=val)
                    else:
                        return FloatLit(value=val)
            return expr

        elif isinstance(expr, Comparison):
            expr.left = self.fold_expr(expr.left)
            expr.right = self.fold_expr(expr.right)
            if isinstance(expr.left, (IntLit, FloatLit, BoolLit, StringLit)) and isinstance(expr.right, (IntLit, FloatLit, BoolLit, StringLit)):
                lval = expr.left.value
                rval = expr.right.value
                val = None
                try:
                    if expr.op == "==":
                        val = lval == rval
                    elif expr.op == "!=":
                        val = lval != rval
                    elif expr.op == "<":
                        val = lval < rval
                    elif expr.op == "<=":
                        val = lval <= rval
                    elif expr.op == ">":
                        val = lval > rval
                    elif expr.op == ">=":
                        val = lval >= rval
                    elif expr.op == "=~":
                        if isinstance(lval, str) and isinstance(rval, str):
                            val = lval.lower() == rval.lower()
                except Exception:
                    pass
                
                if val is not None:
                    return BoolLit(value=val)
            return expr

        elif isinstance(expr, LogicalOp):
            expr.left = self.fold_expr(expr.left)
            expr.right = self.fold_expr(expr.right)
            if isinstance(expr.left, BoolLit) and isinstance(expr.right, BoolLit):
                lval = expr.left.value
                rval = expr.right.value
                if expr.op == "and":
                    return BoolLit(value=lval and rval)
                elif expr.op == "or":
                    return BoolLit(value=lval or rval)
            return expr

        elif isinstance(expr, Negation):
            expr.expr = self.fold_expr(expr.expr)
            if isinstance(expr.expr, BoolLit):
                return BoolLit(value=not expr.expr.value)
            return expr

        elif isinstance(expr, NullCheck):
            expr.col = self.fold_expr(expr.col)
            if isinstance(expr.col, (IntLit, FloatLit, BoolLit, StringLit, DatetimeLit)):
                return BoolLit(value=not expr.is_null)
            return expr

        elif isinstance(expr, IffExpr):
            expr.condition = self.fold_expr(expr.condition)
            expr.true_val = self.fold_expr(expr.true_val)
            expr.false_val = self.fold_expr(expr.false_val)
            if isinstance(expr.condition, BoolLit):
                if expr.condition.value:
                    return expr.true_val
                else:
                    return expr.false_val
            return expr

        elif isinstance(expr, FuncCall):
            expr.args = [self.fold_expr(arg) for arg in expr.args]
            # Protect/Evict non-pure runtime functions (ago, now, rand, new_guid)
            if expr.name in ("ago", "now", "rand", "new_guid"):
                return expr
                
            # Fold pure built-in functions
            if expr.name == "strcat":
                if all(isinstance(arg, (StringLit, IntLit, FloatLit, BoolLit)) for arg in expr.args):
                    concatenated = "".join(str(arg.value) for arg in expr.args)
                    return StringLit(value=concatenated)
            elif expr.name == "tostring":
                if len(expr.args) == 1 and isinstance(expr.args[0], (StringLit, IntLit, FloatLit, BoolLit)):
                    return StringLit(value=str(expr.args[0].value))
            elif expr.name == "toint":
                if len(expr.args) == 1 and isinstance(expr.args[0], (StringLit, IntLit, FloatLit, BoolLit)):
                    try:
                        return IntLit(value=int(expr.args[0].value))
                    except Exception:
                        pass
            elif expr.name == "todouble":
                if len(expr.args) == 1 and isinstance(expr.args[0], (StringLit, IntLit, FloatLit, BoolLit)):
                    try:
                        return FloatLit(value=float(expr.args[0].value))
                    except Exception:
                        pass
            elif expr.name == "tobool":
                if len(expr.args) == 1 and isinstance(expr.args[0], (StringLit, IntLit, FloatLit, BoolLit)):
                    val = expr.args[0].value
                    if isinstance(val, str):
                        bval = val.lower() == "true"
                    else:
                        bval = bool(val)
                    return BoolLit(value=bval)
            return expr

        elif isinstance(expr, SubqueryInExpr):
            expr.col = self.fold_expr(expr.col)
            self.scope_manager.push_scope(ScopeType.SUBQUERY)
            expr.subquery = self.fold_query(expr.subquery)
            self.scope_manager.pop_scope()
            return expr

        elif isinstance(expr, InExpr):
            expr.col = self.fold_expr(expr.col)
            expr.values = [self.fold_expr(v) for v in expr.values]
            return expr

        elif isinstance(expr, StringOp):
            expr.col = self.fold_expr(expr.col)
            return expr

        elif isinstance(expr, HasAnyExpr):
            expr.col = self.fold_expr(expr.col)
            expr.values = [self.fold_expr(v) for v in expr.values]
            return expr

        elif isinstance(expr, BinExpr):
            expr.col = self.fold_expr(expr.col)
            return expr

        return expr
