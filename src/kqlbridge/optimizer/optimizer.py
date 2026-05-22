from __future__ import annotations
import copy
from typing import List, TYPE_CHECKING
from kqlbridge.plugins import get_optimizers

if TYPE_CHECKING:
    from kqlbridge.ast_nodes import KQLQuery

class OptimizationRule:
    """
    Abstract base class for all AST optimization rules.
    Rules modify the AST in place or return a new AST.
    """
    def apply(self, query: KQLQuery) -> KQLQuery:
        raise NotImplementedError("Each optimization rule must implement apply()")

class ASTOptimizer:
    """
    Compiler-grade AST Optimizer.
    Copies the KQL AST prior to applying rules to prevent side-effects,
    then executes registered optimization passes.
    """
    def __init__(self, rules: List[OptimizationRule] | None = None):
        if rules is None:
            # Standard rules
            from .rules.merge_filters import MergeFiltersRule
            from .rules.predicate_pushdown import PredicatePushdownRule
            from .rules.join_rewrite import JoinRewriteRule
            
            self.rules = [
                MergeFiltersRule(),
                PredicatePushdownRule(),
                JoinRewriteRule(),
            ]
        else:
            self.rules = rules

    def optimize(self, query: KQLQuery) -> KQLQuery:
        """
        Produce a highly optimized copy of the input KQL AST.
        """
        # Deepcopy the AST to fully preserve input AST structure
        optimized_query = copy.deepcopy(query)
        
        # Apply standard rules
        for rule in self.rules:
            optimized_query = rule.apply(optimized_query)
            
        # Apply dynamically registered plugin rules
        plugin_rules = get_optimizers()
        for rule_class_or_fn in plugin_rules:
            if isinstance(rule_class_or_fn, type) and issubclass(rule_class_or_fn, OptimizationRule):
                rule_inst = rule_class_or_fn()
                optimized_query = rule_inst.apply(optimized_query)
            elif callable(rule_class_or_fn):
                res = rule_class_or_fn(optimized_query)
                if res is not None:
                    optimized_query = res
                
        return optimized_query
