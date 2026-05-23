"""
explain.py — KQLBridge Translation Annotator
=============================================
AGENT MODIFIABLE — add new annotations here following the _Annotation pattern.

Produces annotated SQL with inline comments explaining every semantic
decision made during KQL → SQL translation. Designed for:

  - MCT training: students see exactly WHY the SQL looks the way it does
  - Enterprise review: migration teams validate translation intent
  - Debugging: identify where translation diverges from expectation

Usage:
    from kqlbridge.explain import explain
    result = explain("AppLogs | where Level == 'Error' | take 10")
    print(result.annotated_sql)
    print(result.summary)
"""

from __future__ import annotations
from dataclasses import dataclass, field

from .ast_nodes import (
    KQLQuery, WhereOp, ProjectOp, SummarizeOp, OrderOp, TakeOp,
    DistinctOp, ExtendOp, JoinOp, UnionOp, CountOp,
    AgoExpr, BinGroup, Comparison, StringOp, InExpr, LogicalOp,
    IffExpr, SubqueryInExpr,
)


# ─── Result types ────────────────────────────────────────────────────────────

@dataclass
class ExplainResult:
    kql: str
    sql: str
    annotated_sql: str
    annotations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        lines = ["KQL → SQL Translation Summary"]
        lines.append("=" * 45)
        lines.append(f"Operators translated: {len(self.annotations)}")
        if self.warnings:
            lines.append(f"Semantic warnings   : {len(self.warnings)}")
        lines.append("")
        for i, note in enumerate(self.annotations, 1):
            lines.append(f"  {i:2}. {note}")
        if self.warnings:
            lines.append("")
            lines.append("Semantic drift warnings:")
            for w in self.warnings:
                lines.append(f"  ⚠  {w}")
        return "\n".join(lines)


# ─── Annotation rules ────────────────────────────────────────────────────────

def _annotate_query(query: KQLQuery) -> tuple[list[str], list[str]]:
    """Walk the AST and collect annotations + semantic warnings."""
    notes = []
    warnings = []

    # let bindings → CTEs
    for binding in query.let_bindings:
        notes.append(
            f"let {binding.name} → WITH {binding.name} AS (...) "
            f"[KQL let becomes a SQL Common Table Expression]"
        )

    # pipe operators
    for op in query.pipes:
        _annotate_op(op, notes, warnings)

    return notes, warnings


def _annotate_op(op, notes: list[str], warnings: list[str]) -> None:
    if isinstance(op, WhereOp):
        _annotate_where(op, notes, warnings)

    elif isinstance(op, ProjectOp):
        aliases = op.aliases or {}
        if aliases:
            alias_list = ", ".join(f"{s} AS {a}" for s, a in aliases.items())
            notes.append(f"project col=alias → SELECT {alias_list} [column renaming]")
        else:
            notes.append(
                f"project {', '.join(op.columns[:3])}{'...' if len(op.columns) > 3 else ''} "
                f"→ SELECT specific columns [drops all others]"
            )

    elif isinstance(op, SummarizeOp):
        agg_names = []
        for agg in op.aggregations:
            agg_names.append(type(agg).__name__.replace("Agg", "").lower() + "()")
        gb_parts = []
        for gb in op.group_by:
            if isinstance(gb, BinGroup):
                gb_parts.append(f"bin({gb.amount}{gb.unit})")
                _annotate_bin(gb.amount, gb.unit, notes, warnings)
            else:
                gb_parts.append(str(gb.col) if hasattr(gb.col, '__str__') else "col")
        notes.append(
            f"summarize {', '.join(agg_names)} by {', '.join(gb_parts) or 'nothing'} "
            f"→ SELECT aggs FROM ... GROUP BY"
        )

    elif isinstance(op, OrderOp):
        items = [f"{it.direction.upper()}" for it in op.items]
        notes.append(
            f"order by → ORDER BY {', '.join(items)} "
            f"[KQL 'sort by' is identical — both map to ORDER BY]"
        )

    elif isinstance(op, TakeOp):
        notes.append(
            f"take {op.n} → LIMIT {op.n} (Spark) / TOP {op.n} (T-SQL) "
            f"[non-deterministic without order by]"
        )

    elif isinstance(op, DistinctOp):
        if op.star:
            notes.append("distinct * → SELECT DISTINCT * [deduplicates all columns]")
        else:
            notes.append(
                f"distinct {', '.join(op.columns)} → SELECT DISTINCT {', '.join(op.columns)}"
            )

    elif isinstance(op, ExtendOp):
        for alias, expr in op.assignments:
            expr_note = _expr_note(expr)
            notes.append(f"extend {alias} = {expr_note} → SELECT *, expr AS {alias}")
            if isinstance(expr, IffExpr):
                notes.append(
                    "  iff() → CASE WHEN ... THEN ... ELSE ... END "
                    "[KQL conditional maps to SQL CASE expression]"
                )

    elif isinstance(op, JoinOp):
        kind_map = {
            "inner": "INNER JOIN",
            "leftouter": "LEFT OUTER JOIN",
            "rightouter": "RIGHT OUTER JOIN",
            "fullouter": "FULL OUTER JOIN",
        }
        sql_join = kind_map.get(op.kind, "INNER JOIN")
        notes.append(
            f"join kind={op.kind} on {', '.join(op.keys)} → {sql_join} ON key = key "
            f"[KQL join always requires explicit key columns]"
        )

    elif isinstance(op, UnionOp):
        subqueries = op.subqueries or {}
        sub_count = len(subqueries)
        notes.append(
            f"union {', '.join(op.tables[:3])} → UNION ALL "
            f"[KQL union is always UNION ALL — no implicit deduplication"
            + (f"; {sub_count} inline subquer{'y' if sub_count == 1 else 'ies'} translated]"
               if sub_count else "]")
        )

    elif isinstance(op, CountOp):
        notes.append(
            "count → SELECT COUNT(*) AS count_ "
            "[trailing underscore avoids SQL reserved word collision]"
        )


def _annotate_where(op: WhereOp, notes: list[str], warnings: list[str]) -> None:
    _walk_condition(op.condition, notes, warnings)


def _walk_condition(node, notes: list[str], warnings: list[str]) -> None:
    if isinstance(node, Comparison):
        if node.op == "=~":
            warnings.append(
                "=~ is case-insensitive in KQL but translates to = (case-sensitive) in SQL. "
                "Use LOWER() on both sides for correct behaviour."
            )
            notes.append("where col =~ val → WHERE col = val [⚠ case-insensitive → case-sensitive]")
        elif node.op == "==":
            notes.append("where col == val → WHERE col = val [KQL == becomes SQL =]")
        else:
            notes.append(f"where col {node.op} val → WHERE clause")

    elif isinstance(node, StringOp):
        if node.op == "has":
            warnings.append(
                f"has '{node.value}' is word-boundary aware in KQL. "
                f"SQL LIKE '%{node.value}%' matches partial words too."
            )
            notes.append(f"where col has '{node.value}' → WHERE col LIKE '% {node.value} %' [⚠ word-boundary lost]")
        elif node.op == "contains":
            notes.append(f"where col contains '{node.value}' → WHERE col LIKE '%{node.value}%'")
        elif node.op == "startswith":
            notes.append(f"where col startswith '{node.value}' → WHERE col LIKE '{node.value}%'")
        elif node.op == "endswith":
            notes.append(f"where col endswith '{node.value}' → WHERE col LIKE '%{node.value}'")

    elif isinstance(node, InExpr):
        if node.negated:
            notes.append("where col !in (...) → WHERE col NOT IN (...)")
        else:
            notes.append("where col in (...) → WHERE col IN (...)")

    elif isinstance(node, SubqueryInExpr):
        tbl = node.subquery.table if hasattr(node.subquery, 'table') else "subquery"
        if node.negated:
            notes.append(f"where col !in (Table | ...) → WHERE col NOT IN (SELECT ... FROM {tbl})")
        else:
            notes.append(f"where col in (Table | ...) → WHERE col IN (SELECT ... FROM {tbl})")

    elif isinstance(node, LogicalOp):
        _walk_condition(node.left, notes, warnings)
        _walk_condition(node.right, notes, warnings)


def _annotate_bin(amount: int, unit: str, notes: list[str], warnings: list[str]) -> None:
    if unit == "d" and amount >= 7:
        warnings.append(
            f"bin(col, {amount}d) buckets from Unix epoch (Thu Jan 1 1970), "
            f"not calendar {'weeks' if amount == 7 else f'{amount}-day periods'}. "
            f"Use DATE_TRUNC('week', col) for Monday-aligned weeks."
        )
        notes.append(
            f"bin(col, {amount}d) → DATEADD/FLOOR logic [⚠ epoch-relative, not calendar weeks]"
        )
    else:
        unit_map = {"d": "day", "h": "hour", "m": "minute", "s": "second"}
        sql_unit = unit_map.get(unit, unit)
        notes.append(f"bin(col, {amount}{unit}) → DATE_TRUNC('{sql_unit}', col)")


def _expr_note(expr) -> str:
    if isinstance(expr, AgoExpr):
        return f"ago({expr.amount}{expr.unit})"
    if isinstance(expr, IffExpr):
        return "iff(condition, true_val, false_val)"
    if hasattr(expr, 'name'):
        return str(expr.name)
    if hasattr(expr, 'value'):
        return str(expr.value)
    return type(expr).__name__


# ─── Annotated SQL builder ────────────────────────────────────────────────────

def _build_annotated_sql(sql: str, notes: list[str], warnings: list[str], is_python: bool = False) -> str:
    """
    Prepend a header comment block to the SQL/Python with all annotations.
    """
    if is_python:
        lines = ["# KQLBridge Translation Annotations"]
        lines.append("# " + "─" * 50)
        for i, note in enumerate(notes, 1):
            lines.append(f"# {i:2}. {note}")
        if warnings:
            lines.append("#")
            lines.append("# ⚠  Semantic drift warnings:")
            for w in warnings:
                # wrap at 70 chars
                words = w.split()
                line = "#    "
                for word in words:
                    if len(line) + len(word) > 75:
                        lines.append(line.rstrip())
                        line = "#    " + word + " "
                    else:
                        line += word + " "
                lines.append(line.rstrip())
        lines.append("")
        lines.append(sql)
        return "\n".join(lines)
    else:
        lines = ["/* KQLBridge Translation Annotations"]
        lines.append(" * " + "─" * 50)
        for i, note in enumerate(notes, 1):
            lines.append(f" * {i:2}. {note}")
        if warnings:
            lines.append(" *")
            lines.append(" * ⚠  Semantic drift warnings:")
            for w in warnings:
                # wrap at 70 chars
                words = w.split()
                line = " *    "
                for word in words:
                    if len(line) + len(word) > 75:
                        lines.append(line.rstrip())
                        line = " *    " + word + " "
                    else:
                        line += word + " "
                lines.append(line.rstrip())
        lines.append(" */")
        lines.append("")
        lines.append(sql)
        return "\n".join(lines)


# ─── Public API ──────────────────────────────────────────────────────────────

def explain(kql: str, target: str = "spark") -> ExplainResult:
    """
    Translate KQL and return annotated SQL with inline explanations.

    Args:
        kql:    KQL query string
        target: "spark" (default), "tsql", or "pyspark"

    Returns:
        ExplainResult with .annotated_sql, .summary, .annotations, .warnings
    """
    from .parser import parse
    from lark.exceptions import UnexpectedInput as _LarkUnexpectedInput
    from .generators.spark_sql import SparkSQLGenerator
    from .generators.tsql import TSQLGenerator
    from .generators.pyspark import PySparkGenerator

    try:
        query = parse(kql)
    except _LarkUnexpectedInput as e:
        raise ValueError(
            f"Unsupported KQL syntax. Use is_supported() to check first.\n{e}"
        ) from None

    if target == "tsql":
        gen = TSQLGenerator()
    elif target == "pyspark":
        gen = PySparkGenerator()
    else:
        gen = SparkSQLGenerator()
        
    sql = gen.generate(query)

    notes, warnings = _annotate_query(query)
    annotated = _build_annotated_sql(sql, notes, warnings, is_python=(target == "pyspark"))

    return ExplainResult(
        kql=kql,
        sql=sql,
        annotated_sql=annotated,
        annotations=notes,
        warnings=warnings,
    )


@dataclass(slots=True)
class SymbolLineageNode:
    name: str
    symbol_id: int
    origin_node: str
    origin_scope: int
    dependencies: list[SymbolLineageNode] = field(default_factory=list)


@dataclass(slots=True)
class ExplainSemanticResult:
    target_dialect: str
    symbols: list[SymbolLineageNode] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    optimization_rules_applied: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        """Generates clean ASCII tree renderings for console visualization."""
        lines = [f"Semantic Explanation Report [{self.target_dialect.upper()}]", "=" * 50]
        for sym in self.symbols:
            lines.extend(self._render_tree(sym, depth=0))
        return "\n".join(lines)

    def _render_tree(self, node: SymbolLineageNode, depth: int) -> list[str]:
        indent = "    " * depth
        marker = "└── " if depth > 0 else ""
        lines = [f"{indent}{marker}{node.name} [id={node.symbol_id}, node={node.origin_node}]"]
        for child in node.dependencies:
            lines.extend(self._render_tree(child, depth + 1))
        return lines

    def to_dict(self) -> dict:
        """JSON-serialisable representation for APIs."""
        return {
            "target_dialect": self.target_dialect,
            "symbols": [self._node_to_dict(sym) for sym in self.symbols],
            "warnings": self.warnings,
            "optimization_rules_applied": self.optimization_rules_applied
        }

    def _node_to_dict(self, node: SymbolLineageNode) -> dict:
        return {
            "name": node.name,
            "symbol_id": node.symbol_id,
            "origin_node": node.origin_node,
            "origin_scope": node.origin_scope,
            "dependencies": [self._node_to_dict(dep) for dep in node.dependencies]
        }


def explain_semantic(kql: str, target: str = "spark") -> ExplainSemanticResult:
    """
    Translate KQL and return a structured semantic lineage report.
    """
    from .parser import parse
    from .scoping import ScopeManager, SymbolInfo, SymbolKind
    from .passes.alpha_renaming import AlphaRenamer
    from .passes.constant_folding import ConstantFolder
    from .optimizer import ASTOptimizer
    from .ir import (
        to_semantic_ir, SemanticQuery, SemanticProjection, SemanticAggregate,
        SemanticJoin, SemanticUnion, SemanticColumnRef, SemanticComparison,
        SemanticLogicalOp, SemanticFunctionCall
    )
    from .ast_nodes import WhereOp, Comparison, StringOp, LogicalOp

    # 1. Parse and resolve scopes, constant fold, and optimize AST
    query = parse(kql)
    scope_manager = ScopeManager()
    query = AlphaRenamer(scope_manager).rename_query(query)
    query = ConstantFolder(scope_manager).fold_query(query)
    query = ASTOptimizer().optimize(query)

    # 2. Translate AST to Semantic IR
    ir_query = to_semantic_ir(query, scope_manager.current_scope)

    # 3. Walk IR and construct global registry mapping symbol_id to definition nodes
    registry: dict[int, dict[str, Any]] = {}
    registry_ctes: dict[str, SemanticQuery] = {}

    def lookup_name_recursive(table: Any, name: str) -> Any:
        curr = table
        while curr is not None:
            sym = curr.lookup_local(name)
            if sym is not None:
                return sym
            curr = curr.parent
        return None

    def get_expr_symbol_ids(expr: Any, scope: Any) -> list[int]:
        ids = []
        if isinstance(expr, SemanticColumnRef):
            sym = lookup_name_recursive(scope, expr.name) if scope else None
            if sym:
                ids.append(sym.symbol_id)
            else:
                if expr.symbol_id != 0:
                    ids.append(expr.symbol_id)
        elif isinstance(expr, SemanticComparison):
            ids.extend(get_expr_symbol_ids(expr.left, scope))
            ids.extend(get_expr_symbol_ids(expr.right, scope))
        elif isinstance(expr, SemanticLogicalOp):
            for e in expr.expressions:
                ids.extend(get_expr_symbol_ids(e, scope))
        elif isinstance(expr, SemanticFunctionCall):
            for arg in expr.arguments:
                ids.extend(get_expr_symbol_ids(arg, scope))
        return ids

    def walk_ir(node: Any):
        if not node:
            return
        if isinstance(node, SemanticQuery):
            # Walk CTEs and register them
            for name, cte in node.ctes.items():
                registry_ctes[name] = cte
                walk_ir(cte)
            # Walk source if subquery
            if isinstance(node.source, SemanticQuery):
                walk_ir(node.source)
            elif isinstance(node.source, list):
                for src in node.source:
                    if isinstance(src, SemanticQuery):
                        walk_ir(src)
            
            # Bridge CTE boundaries
            cte_query = None
            if isinstance(node.source, str) and node.source in registry_ctes:
                cte_query = registry_ctes[node.source]

            # Register scope symbols
            curr = node.symbol_table
            while curr is not None:
                for sym in curr.symbols.values():
                    origin = type(sym.origin_node).__name__ if sym.origin_node is not None else "None"
                    if sym.symbol_id not in registry:
                        deps = list(sym.derived_from) if sym.derived_from else []
                        if cte_query and sym.symbol_kind == SymbolKind.COLUMN:
                            cte_sym = lookup_name_recursive(cte_query.symbol_table, sym.name)
                            if cte_sym:
                                deps.append(cte_sym.symbol_id)
                        registry[sym.symbol_id] = {
                            "name": sym.name,
                            "origin_node": origin,
                            "origin_scope": sym.scope_depth,
                            "dependencies": deps
                        }
                    elif registry[sym.symbol_id]["origin_node"] == "None" and origin != "None":
                        registry[sym.symbol_id]["origin_node"] = origin
                        deps = list(sym.derived_from) if sym.derived_from else []
                        if cte_query and sym.symbol_kind == SymbolKind.COLUMN:
                            cte_sym = lookup_name_recursive(cte_query.symbol_table, sym.name)
                            if cte_sym:
                                deps.append(cte_sym.symbol_id)
                        if deps:
                            registry[sym.symbol_id]["dependencies"] = deps
                curr = curr.parent
            # Walk query steps
            for step in node.steps:
                if isinstance(step, SemanticProjection):
                    for item in step.items:
                        deps = []
                        for dep_id in item.derived_from:
                            if dep_id == 0 and isinstance(item.expression, SemanticColumnRef):
                                sym = lookup_name_recursive(node.symbol_table.parent, item.expression.name) if node.symbol_table.parent else None
                                if sym:
                                    deps.append(sym.symbol_id)
                            else:
                                deps.append(dep_id)
                        if not deps:
                            deps = get_expr_symbol_ids(item.expression, node.symbol_table.parent)
                        origin = type(item.origin_node).__name__ if item.origin_node is not None else "None"
                        if item.symbol_id not in registry or origin != "None":
                            registry[item.symbol_id] = {
                                "name": item.alias,
                                "origin_node": origin,
                                "origin_scope": 0,
                                "dependencies": deps
                            }
                elif isinstance(step, SemanticAggregate):
                    eval_scope = node.symbol_table.parent if node.symbol_table else None
                    for item in step.aggregations:
                        deps = []
                        for arg in item.arguments:
                            deps.extend(get_expr_symbol_ids(arg, eval_scope))
                        deps = sorted(list(set(deps)))
                        origin = type(item.origin_node).__name__ if item.origin_node is not None else "None"
                        if item.symbol_id not in registry or origin != "None":
                            registry[item.symbol_id] = {
                                "name": item.alias,
                                "origin_node": origin,
                                "origin_scope": 0,
                                "dependencies": deps
                            }
                    for item in step.group_by:
                        deps = get_expr_symbol_ids(item.expression, eval_scope)
                        origin = type(item.origin_node).__name__ if item.origin_node is not None else "None"
                        if item.symbol_id not in registry or origin != "None":
                            registry[item.symbol_id] = {
                                "name": item.alias,
                                "origin_node": origin,
                                "origin_scope": 0,
                                "dependencies": deps
                            }
                else:
                    walk_ir(step)
        elif isinstance(node, SemanticJoin):
            walk_ir(node.right_query)
        elif isinstance(node, SemanticUnion):
            for inp in node.inputs:
                walk_ir(inp)
            for sub in node.subqueries.values():
                walk_ir(sub)

    walk_ir(ir_query)

    # 4. Determine output visible columns of terminal query state
    from .scoping import SymbolTable, ScopeType, SymbolKind
    def get_visible_column_symbols_local(symbol_table: SymbolTable) -> list[SymbolInfo]:
        visible = {}
        curr = symbol_table
        crossed_subquery = False
        schema_truncated = False

        while curr is not None:
            for name, sym in curr.symbols.items():
                if sym.symbol_kind == SymbolKind.COLUMN:
                    if schema_truncated:
                        if name not in curr.grouping_keys:
                            continue
                    if crossed_subquery:
                        continue

                    if name not in visible:
                        visible[name] = sym

            if curr.is_schema_truncated:
                schema_truncated = True
            if curr.scope_type == ScopeType.SUBQUERY:
                crossed_subquery = True
            curr = curr.parent

        return list(visible.values())

    visible_cols = get_visible_column_symbols_local(ir_query.symbol_table)

    def build_lineage_node(sym_id: int, path_visited: set[int]) -> SymbolLineageNode:
        entry = registry.get(sym_id)
        if entry is None:
            return SymbolLineageNode(
                name=f"unknown_col_{sym_id}",
                symbol_id=sym_id,
                origin_node="None",
                origin_scope=0,
                dependencies=[]
            )

        name = entry["name"]
        symbol_id = sym_id
        origin_node = entry["origin_node"]
        origin_scope = entry["origin_scope"]
        derived_from = entry["dependencies"]

        deps: list[SymbolLineageNode] = []
        if sym_id not in path_visited:
            next_visited = path_visited | {sym_id}
            for dep_id in derived_from:
                if dep_id != sym_id:
                    child = build_lineage_node(dep_id, next_visited)
                    if child.name == name:
                        deps.extend(child.dependencies)
                    else:
                        deps.append(child)

        return SymbolLineageNode(
            name=name,
            symbol_id=symbol_id,
            origin_node=origin_node,
            origin_scope=origin_scope,
            dependencies=deps
        )

    symbols_lineage: list[SymbolLineageNode] = []
    for col in visible_cols:
        symbols_lineage.append(build_lineage_node(col.symbol_id, set()))

    # Walk AST to extract semantic drift warnings
    warnings: list[str] = []
    for pipe in query.pipes:
        if isinstance(pipe, WhereOp):
            def check_cond(node):
                if isinstance(node, Comparison) and node.op == "=~":
                    warnings.append(
                        "=~ is case-insensitive in KQL but translates to = (case-sensitive) in SQL. "
                        "Use LOWER() on both sides for correct behaviour."
                    )
                elif isinstance(node, StringOp) and node.op == "has":
                    warnings.append(
                        f"has '{node.value}' is word-boundary aware in KQL. "
                        f"SQL LIKE '%{node.value}%' matches partial words too."
                    )
                elif isinstance(node, LogicalOp):
                    check_cond(node.left)
                    check_cond(node.right)
            check_cond(pipe.condition)

    opt_rules = ["MergeFiltersRule", "PredicatePushdownRule", "JoinRewriteRule"]

    return ExplainSemanticResult(
        target_dialect=target,
        symbols=symbols_lineage,
        warnings=warnings,
        optimization_rules_applied=opt_rules
    )

