from __future__ import annotations
import inspect
from typing import Callable, Dict, Tuple, List, Type, Any

# Global registries for plugins
_RENDERERS: Dict[Tuple[Type, str], Callable] = {}
_OPTIMIZERS: List[Any] = []

def register_renderer(node_type: Type, dialect: str):
    """
    Decorator to register a custom renderer for a specific AST node type and target dialect.
    
    The decorated function should match the signature:
        def custom_renderer(generator, node) -> str:
            ...
            
    Example:
        @register_renderer(node_type=SummarizeOp, dialect="spark")
        def render_summarize(generator, node):
            ...
    """
    def decorator(func: Callable):
        _RENDERERS[(node_type, dialect.lower())] = func
        return func
    return decorator

def register_optimizer(cls_or_fn: Any):
    """
    Decorator to register a custom optimizer pass or optimization rule.
    
    Example:
        @register_optimizer
        class PushPredicateIntoJoin(OptimizationRule):
            def apply(self, query):
                ...
    """
    if cls_or_fn not in _OPTIMIZERS:
        _OPTIMIZERS.append(cls_or_fn)
    return cls_or_fn

def get_renderer(node_type: Type, dialect: str) -> Callable | None:
    """
    Retrieve the custom renderer for a given AST node type and target dialect.
    """
    return _RENDERERS.get((node_type, dialect.lower()))

def get_optimizers() -> List[Any]:
    """
    Retrieve all registered custom optimizers/rules.
    """
    return list(_OPTIMIZERS)

# Backward-compatibility fallback decorators
def register_operator(name: str):
    """
    Backward-compatibility decorator for operator registration.
    """
    def decorator(func: Callable):
        return func
    return decorator

def register_function(name: str):
    """
    Backward-compatibility decorator for function registration.
    """
    def decorator(func: Callable):
        return func
    return decorator
