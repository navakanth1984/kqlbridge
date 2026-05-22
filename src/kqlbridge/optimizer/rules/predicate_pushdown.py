from __future__ import annotations
from typing import TYPE_CHECKING, List, Set
from kqlbridge.optimizer.optimizer import OptimizationRule
from kqlbridge.ast_nodes import WhereOp, ProjectOp, ExtendOp, OrderOp, ColumnRef

if TYPE_CHECKING:
    from kqlbridge.ast_nodes import KQLQuery

def get_referenced_columns(expr) -> Set[str]:
    """
    Recursively extract all column names referenced in an AST expression.
    """
    if isinstance(expr, ColumnRef):
        return {expr.name}
    cols = set()
    if hasattr(expr, "__dict__"):
        for k, v in expr.__dict__.items():
            if isinstance(v, list):
                for item in v:
                    cols.update(get_referenced_columns(item))
            else:
                cols.update(get_referenced_columns(v))
    return cols

class PredicatePushdownRule(OptimizationRule):
    """
    Optimization rule that pushes 'where' predicates upstream (earlier in the pipeline),
    past operators like 'project', 'extend', or 'order by', if safe to do so.
    
    This reduces the rows processed in subsequent steps.
    """
    def apply(self, query: KQLQuery) -> KQLQuery:
        pipes = list(query.pipes)
        changed = True
        
        # Keep bubbling predicates upstream until no more swaps are safe/possible
        while changed:
            changed = False
            for i in range(1, len(pipes)):
                current = pipes[i]
                prev = pipes[i - 1]
                
                if isinstance(current, WhereOp):
                    # Check if we can push current WhereOp past prev operator
                    can_push = False
                    
                    if isinstance(prev, OrderOp):
                        # Pushing past order by is always safe and highly recommended
                        can_push = True
                        
                    elif isinstance(prev, ProjectOp):
                        # Safe if the where clause does not reference any alias defined in project
                        where_cols = get_referenced_columns(current.condition)
                        project_aliases = set(prev.aliases.values()) if prev.aliases else set()
                        # If a column was renamed/created as an alias, we can't push unless we rename it,
                        # so let's check intersection.
                        if not (where_cols & project_aliases):
                            can_push = True
                            
                    elif isinstance(prev, ExtendOp):
                        # Safe if where clause does not reference any column assigned in extend
                        where_cols = get_referenced_columns(current.condition)
                        extended_cols = {alias for alias, _ in prev.assignments}
                        if not (where_cols & extended_cols):
                            can_push = True
                            
                    if can_push:
                        # Swap them!
                        pipes[i], pipes[i - 1] = pipes[i - 1], pipes[i]
                        changed = True
                        break
                        
        query.pipes = pipes
        return query
