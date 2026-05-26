import json
from typing import Any
from .nodes import (
    SemanticQuery, SemanticFilter, SemanticProjection,
    ProjectionItem, SemanticAggregate, AggregateItem, SemanticJoin,
    SemanticUnion, SemanticColumnRef, SemanticLiteral,
    SemanticComparison, SemanticLogicalOp, SemanticFunctionCall, SemanticSubquery,
    SemanticJoinCondition, UnionColumnMapping
)

def serialize_ir_to_dict(node: Any) -> Any:
    """Recursively serializes any Semantic IR node or collection to a deterministic dictionary/list."""
    if node is None:
        return None
        
    if isinstance(node, (str, int, float, bool)):
        return node

    if isinstance(node, list):
        return [serialize_ir_to_dict(item) for item in node]

    if isinstance(node, dict):
        return {str(k): serialize_ir_to_dict(v) for k, v in sorted(node.items())}

    if isinstance(node, SemanticQuery):
        return {
            "type": "SemanticQuery",
            "source": serialize_ir_to_dict(node.source),
            "source_table": node.source_table,
            "step_count": len(node.steps),
            "steps": [serialize_ir_to_dict(s) for s in node.steps],
            "ctes": {k: serialize_ir_to_dict(v) for k, v in sorted(node.ctes.items())},
            "pipeline_state": {k: serialize_ir_to_dict(v) for k, v in sorted(node.pipeline_state.items())}
        }

    if isinstance(node, SemanticFilter):
        return {
            "type": "SemanticFilter",
            "predicate": serialize_ir_to_dict(node.predicate)
        }

    if isinstance(node, SemanticProjection):
        # Sort items by alias to enforce deterministic snapshot ordering
        sorted_items = sorted(node.items, key=lambda x: x.alias)
        return {
            "type": "SemanticProjection",
            "items": [serialize_ir_to_dict(item) for item in sorted_items],
            "is_extend_only": node.is_extend_only
        }

    if isinstance(node, ProjectionItem):
        return {
            "type": "ProjectionItem",
            "alias": node.alias,
            "expression": serialize_ir_to_dict(node.expression),
            "symbol_id": node.symbol_id,
            "derived_from": sorted(node.derived_from),
            "origin_node_type": type(node.origin_node).__name__ if node.origin_node else None
        }

    if isinstance(node, SemanticAggregate):
        sorted_aggs = sorted(node.aggregations, key=lambda x: x.alias)
        sorted_gb = sorted(node.group_by, key=lambda x: x.alias)
        return {
            "type": "SemanticAggregate",
            "aggregations": [serialize_ir_to_dict(agg) for agg in sorted_aggs],
            "group_by": [serialize_ir_to_dict(gb) for gb in sorted_gb]
        }

    if isinstance(node, AggregateItem):
        return {
            "type": "AggregateItem",
            "alias": node.alias,
            "function_name": node.function_name,
            "arguments": [serialize_ir_to_dict(arg) for arg in node.arguments],
            "symbol_id": node.symbol_id,
            "derived_from": sorted(node.derived_from),
            "origin_node_type": type(node.origin_node).__name__ if node.origin_node else None,
            "is_distinct": node.is_distinct
        }

    if isinstance(node, SemanticJoinCondition):
        return {
            "type": "SemanticJoinCondition",
            "left_symbol_id": node.left_symbol_id,
            "right_symbol_id": node.right_symbol_id,
            "left_col": node.left_col,
            "right_col": node.right_col,
            "operator": node.operator
        }

    if isinstance(node, SemanticJoin):
        return {
            "type": "SemanticJoin",
            "right_query": serialize_ir_to_dict(node.right_query),
            "kind": node.kind,
            "conditions": [serialize_ir_to_dict(c) for c in node.conditions],
            "on_keys": sorted(node.on_keys)
        }

    if isinstance(node, UnionColumnMapping):
        return {
            "type": "UnionColumnMapping",
            "output_alias": node.output_alias,
            "source_mappings": {str(k): v for k, v in sorted(node.source_mappings.items())},
            "is_nullable": node.is_nullable
        }

    if isinstance(node, SemanticUnion):
        return {
            "type": "SemanticUnion",
            "tables": sorted(node.tables),
            "inputs": [serialize_ir_to_dict(i) for i in node.inputs],
            "mappings": [serialize_ir_to_dict(m) for m in sorted(node.mappings, key=lambda x: x.output_alias)]
        }

    if isinstance(node, SemanticColumnRef):
        return {
            "type": "SemanticColumnRef",
            "name": node.name,
            "symbol_id": node.symbol_id
        }

    if isinstance(node, SemanticLiteral):
        return {
            "type": "SemanticLiteral",
            "value": str(node.value)
        }

    if isinstance(node, SemanticComparison):
        return {
            "type": "SemanticComparison",
            "left": serialize_ir_to_dict(node.left),
            "op": node.op,
            "right": serialize_ir_to_dict(node.right)
        }

    if isinstance(node, SemanticLogicalOp):
        return {
            "type": "SemanticLogicalOp",
            "op": node.op,
            "expressions": [serialize_ir_to_dict(e) for e in node.expressions]
        }

    if isinstance(node, SemanticFunctionCall):
        return {
            "type": "SemanticFunctionCall",
            "name": node.name,
            "arguments": [serialize_ir_to_dict(arg) for arg in node.arguments]
        }

    if isinstance(node, SemanticSubquery):
        return {
            "type": "SemanticSubquery",
            "query": serialize_ir_to_dict(node.query)
        }

    # Fallback for unknown classes or AST nodes
    return f"<{type(node).__name__}>"

def serialize_ir_to_json(node: SemanticQuery, indent: int = 2) -> str:
    """Serializes a SemanticQuery IR envelope deterministically into a formatted JSON string."""
    return json.dumps(serialize_ir_to_dict(node), indent=indent)
