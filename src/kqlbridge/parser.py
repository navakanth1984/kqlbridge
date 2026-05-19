"""
parser.py — KQLBridge Lark Parse Tree → KQL AST
================================================
AGENT MODIFIABLE — This is the primary file the BIT loop improves.

Rules for the agent:
1. Every change must trace to a failing benchmark case (cite the ID).
2. Do not touch _translate_expr() while fixing _summarize().
   Touch only the method that maps to the failing operator.
3. Do not add abstractions until the same pattern appears ≥ 3 times.
4. After any change: run prepare.py and report the score delta.

Karpathy Principle 2: one method per operator, no speculative abstraction.
"""

from __future__ import annotations
import re as _re
from pathlib import Path
from lark import Lark, Tree, Token

from .ast_nodes import (
    KQLQuery, LetBinding, PipeOp,
    # Operators
    WhereOp, ProjectOp, SummarizeOp, OrderOp, TakeOp,
    DistinctOp, ExtendOp, JoinOp, UnionOp, CountOp, SerializeOp,
    # Aggregations
    AggCount, AggSum, AggAvg, AggMin, AggMax, AggDCount, AggCountIf, AggPercentile, AggMakeList,
    # Groupby
    BinGroup, PlainGroup,
    # Expressions
    ColumnRef, StringLit, IntLit, FloatLit, BoolLit, AgoExpr, BinExpr,
    FuncCall, BinaryOp,
    # Bool expressions
    Comparison, InExpr, StringOp, NullCheck, LogicalOp, Negation, HasAnyExpr,
    # Order
    OrderItem, DatetimeLit, IffExpr, SubqueryInExpr,
)

_GRAMMAR_FILE = Path(__file__).parent / "grammar" / "kql.lark"

# Optimization: Lazily load the Lark parser to significantly improve module import time.
# The Lark parser initialization takes ~50-100ms, which is unnecessary if we are only importing.
_parser = None

def get_parser() -> Lark:
    global _parser
    if _parser is None:
        _parser = Lark(
            _GRAMMAR_FILE.read_text(),
            parser="earley",
            ambiguity="resolve",
        )
    return _parser

# ─── TIMEUNIT MAPPING ────────────────────────────────────────────────────────
# KQL timespan unit → SQL INTERVAL unit string
_TIMEUNIT_MAP = {
    "d": "days",
    "h": "hours",
    "m": "minutes",
    "s": "seconds",
    "ms": "milliseconds",
}


# KQL keywords that must be lowercased before parsing (case-insensitive in spec)
_KQL_KEYWORDS = {
    "where", "project", "summarize", "order", "sort", "by", "take", "limit",
    "distinct", "extend", "join", "union", "count", "let",
    "and", "or", "not", "in", "has", "contains", "startswith", "endswith",
    "matches", "regex", "asc", "desc", "kind", "inner", "leftouter",
    "rightouter", "fullouter", "on", "true", "false", "ago", "bin",
    "sum", "avg", "min", "max", "dcount", "countif", "isnotnull", "isnull",
}


# Optimization: Pre-compile word matching regex.
# Using match with a start position parameter (`_WORD_RE.match(kql, i)`)
# avoids O(N^2) string slicing `kql[i:]` on long queries.
_WORD_RE = _re.compile(r'[A-Za-z_][A-Za-z0-9_.]*')
_COMP_OP_RE = _re.compile(r"(?i)\s*(?:==|!=|<=|>=|<|>|=~|!in\b|in\b|has\b|contains\b|startswith\b|endswith\b)")

def _normalize_keywords(kql: str) -> str:
    """Lowercase KQL keywords while preserving quoted string content."""
    result = []
    i = 0
    kql_len = len(kql)
    while i < kql_len:
        if kql[i] in ('"', "'"):
            q = kql[i]
            j = i + 1
            while j < kql_len and kql[j] != q:
                j += 1
            result.append(kql[i:j + 1])
            i = j + 1
        else:
            m = _WORD_RE.match(kql, i)
            if m:
                word = m.group()
                result.append(word.lower() if word.lower() in _KQL_KEYWORDS else word)
                i = m.end()
            else:
                result.append(kql[i])
                i += 1
    return ''.join(result)


def _split_case_args(arg_str: str) -> list[str]:
    args = []
    current = []
    paren_depth = 0
    in_single_quote = False
    in_double_quote = False
    
    i = 0
    while i < len(arg_str):
        c = arg_str[i]
        if c == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            current.append(c)
        elif c == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            current.append(c)
        elif in_single_quote or in_double_quote:
            current.append(c)
        elif c == '(':
            paren_depth += 1
            current.append(c)
        elif c == ')':
            paren_depth -= 1
            current.append(c)
        elif c == ',' and paren_depth == 0:
            args.append("".join(current).strip())
            current = []
        else:
            current.append(c)
        i += 1
    if current:
        args.append("".join(current).strip())
    return args

def _build_iff_chain(args: list[str]) -> str:
    if len(args) == 0:
        return ""
    if len(args) == 1:
        return args[0]
    if len(args) == 2:
        return f"iff({args[0]}, {args[1]}, null)"
    cond = args[0]
    val = args[1]
    rest = args[2:]
    return f"iff({cond}, {val}, {_build_iff_chain(rest)})"

def _preprocess_case(kql: str) -> str:
    pattern = _re.compile(r"\bcase\b\s*\(", _re.IGNORECASE)
    
    while True:
        match = pattern.search(kql)
        if not match:
            break
        
        start_idx = match.start()
        open_paren_idx = match.end() - 1
        
        paren_depth = 1
        in_single_quote = False
        in_double_quote = False
        close_paren_idx = -1
        
        for i in range(open_paren_idx + 1, len(kql)):
            c = kql[i]
            if c == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif c == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif in_single_quote or in_double_quote:
                continue
            elif c == '(':
                paren_depth += 1
            elif c == ')':
                paren_depth -= 1
                if paren_depth == 0:
                    close_paren_idx = i
                    break
        
        if close_paren_idx == -1:
            break
            
        arg_str = kql[open_paren_idx + 1:close_paren_idx]
        arg_str_rewritten = _preprocess_case(arg_str)
        args = _split_case_args(arg_str_rewritten)
        iff_chain = _build_iff_chain(args)
        
        kql = kql[:start_idx] + iff_chain + kql[close_paren_idx + 1:]
        
    return kql

def _preprocess_json(kql: str) -> str:
    return _re.sub(
        r"(?i)\bparse_json\(\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\)\.([a-zA-Z0-9_.]+)",
        r"parse_json_path(\1, '\2')",
        kql
    )

def _preprocess_mv_expand(kql: str) -> str:
    return _re.sub(
        r"(?i)\|\s*mv-expand\s+([a-zA-Z_][a-zA-Z0-9_.]*)",
        r"| extend _mv_expand = mv_expand_fn(\1)",
        kql
    )

def _preprocess_bool_funcs(kql: str) -> str:
    pattern = _re.compile(r"\b(ipv4_is_private|ipv4_is_in_range)\s*\(", _re.IGNORECASE)
    i = 0
    while i < len(kql):
        match = pattern.search(kql, i)
        if not match:
            break
        open_paren_idx = match.end() - 1
        paren_depth = 1
        in_single_quote = False
        in_double_quote = False
        close_paren_idx = -1
        for j in range(open_paren_idx + 1, len(kql)):
            c = kql[j]
            if c == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif c == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif in_single_quote or in_double_quote:
                continue
            elif c == '(':
                paren_depth += 1
            elif c == ')':
                paren_depth -= 1
                if paren_depth == 0:
                    close_paren_idx = j
                    break
        if close_paren_idx == -1:
            i = open_paren_idx + 1
            continue

        if not _COMP_OP_RE.match(kql, close_paren_idx + 1):
            kql = kql[:close_paren_idx + 1] + " == true" + kql[close_paren_idx + 1:]
            i = close_paren_idx + 1 + len(" == true")
        else:
            i = close_paren_idx + 1
    return kql

def parse(kql: str) -> KQLQuery:
    """
    Parse a KQL query string into a KQLQuery AST.
    Keywords are normalized to lowercase (KQL is case-insensitive for keywords).
    Raises lark.exceptions.UnexpectedInput on syntax errors.
    """
    # Apply custom preprocessors for SOC threat hunting capabilities
    kql = _preprocess_case(kql)
    kql = _preprocess_json(kql)
    kql = _preprocess_mv_expand(kql)
    kql = _preprocess_bool_funcs(kql)
    
    normalized = _normalize_keywords(kql.strip())
    tree = get_parser().parse(normalized)
    return _build_query(tree)



# ─── TOP-LEVEL BUILDER ───────────────────────────────────────────────────────

def _build_query(tree: Tree) -> KQLQuery:
    let_bindings = []
    table = None
    pipes = []

    for child in tree.children:
        if isinstance(child, Tree):
            if child.data == "let_stmt":
                let_bindings.append(_build_let(child))
            elif child.data == "table_expr":
                table = str(child.children[0])
            elif child.data == "pipe_op":
                op = _build_pipe_op(child)
                # Flatten implicit extends from summarize re-aliasing
                if hasattr(op, "_implicit_extends"):
                    pipes.append(ExtendOp(assignments=op._implicit_extends))
                    del op._implicit_extends
                pipes.append(op)

    if table is None:
        raise ValueError("KQL query has no table expression")

    return KQLQuery(table=table, pipes=pipes, let_bindings=let_bindings)


def _build_let(tree: Tree) -> LetBinding:
    name = str(tree.children[0])
    value_tree = tree.children[1]

    if isinstance(value_tree, Tree) and value_tree.data == "table_ref_expr":
        table = str(value_tree.children[0])
        pipes = []
        for c in value_tree.children[1:]:
            if isinstance(c, Tree) and c.data == "pipe_op":
                op = _build_pipe_op(c)
                if hasattr(op, "_implicit_extends"):
                    pipes.append(ExtendOp(assignments=op._implicit_extends))
                    del op._implicit_extends
                pipes.append(op)
        sub_query = KQLQuery(table=table, pipes=pipes)
    elif isinstance(value_tree, Tree) and value_tree.data == "timespan":
        amount, unit = _build_timespan(value_tree)
        # Standalone timespan in let: treat as ago(N) for now to preserve interval semantic
        expr_node = AgoExpr(amount=amount, unit=unit)
        sub_query = KQLQuery(table="__scalar__", pipes=[])
        sub_query.scalar_expr = expr_node
    else:
        expr_node = _build_expr(value_tree)
        sub_query = KQLQuery(table="__scalar__", pipes=[])
        sub_query.scalar_expr = expr_node

    return LetBinding(name=name, value=sub_query)


# ─── PIPE OPERATORS ──────────────────────────────────────────────────────────

def _build_pipe_op(tree: Tree) -> PipeOp:
    inner = tree.children[0]
    dispatch = {
        "where_op":      _build_where,
        "project_op":    _build_project,
        "summarize_op":  _build_summarize,
        "order_op":      _build_order,
        "take_op":       _build_take,
        "distinct_op":   _build_distinct,
        "extend_op":     _build_extend,
        "join_op":       _build_join,
        "union_op":      _build_union,
        "count_op":      lambda _: CountOp(),
        "serialize_op":  lambda _: SerializeOp(),
    }
    builder = dispatch.get(inner.data)
    if builder is None:
        raise NotImplementedError(f"Parser: operator not implemented: {inner.data}")
    return builder(inner)


def _build_where(tree: Tree) -> WhereOp:
    return WhereOp(condition=_build_bool_expr(tree.children[0]))


def _build_project(tree: Tree) -> ProjectOp:
    project_list = tree.children[0]  # project_list Tree
    columns = []
    aliases = {}
    for item in project_list.children:
        if not isinstance(item, Tree):
            continue
        if item.data == "project_alias":
            # project_alias: NAME "=" NAME  (alias = source)
            alias = str(item.children[0])
            source = str(item.children[1])
            columns.append(source)
            aliases[source] = alias
        else:
            # project_col: NAME
            col = str(item.children[0])
            columns.append(col)
    return ProjectOp(columns=columns, aliases=aliases)


def _build_summarize(tree: Tree) -> SummarizeOp:
    agg_list_tree = None
    groupby_list_tree = None

    for child in tree.children:
        if isinstance(child, Tree):
            if child.data == "agg_list":
                agg_list_tree = child
            elif child.data == "groupby_list":
                groupby_list_tree = child

    aggregations = _build_agg_list(agg_list_tree) if agg_list_tree else []
    
    # Handle re-aliasing in 'by' clause: by Alias=Expr
    # Desugar to implicit extend if needed
    implicit_extends = []
    group_by = []
    
    if groupby_list_tree:
        for item in groupby_list_tree.children:
            if not isinstance(item, Tree):
                continue
            if item.data == "named_group":
                alias = str(item.children[0])
                expr_tree = item.children[1]
                # If it's a plain expression (not bin), we can extend it
                if expr_tree.data == "plain_group_expr":
                    expr_node = _build_expr(expr_tree.children[0])
                    implicit_extends.append((alias, expr_node))
                    group_by.append(PlainGroup(col=ColumnRef(name=alias)))
                elif expr_tree.data == "bin_group_expr":
                    col_node = _build_expr(expr_tree.children[0])
                    amount, unit = _build_timespan(expr_tree.children[1])
                    bin_node = BinExpr(col=col_node, amount=amount, unit=unit)
                    implicit_extends.append((alias, bin_node))
                    group_by.append(PlainGroup(col=ColumnRef(name=alias)))
            elif item.data == "plain_group":
                expr_tree = item.children[0]
                if expr_tree.data == "bin_group_expr":
                    col = _build_expr(expr_tree.children[0])
                    amount, unit = _build_timespan(expr_tree.children[1])
                    group_by.append(BinGroup(col=col, amount=amount, unit=unit))
                else:
                    group_by.append(PlainGroup(col=_build_expr(expr_tree.children[0])))

    op = SummarizeOp(aggregations=aggregations, group_by=group_by)
    if implicit_extends:
        op._implicit_extends = implicit_extends
    return op


def _build_agg_list(tree: Tree) -> list:
    result = []
    for item in tree.children:
        if isinstance(item, Tree) and item.data in ("named_agg", "anon_agg"):
            result.append(_build_agg_item(item))
    return result


def _build_agg_item(tree: Tree):
    if tree.data == "named_agg":
        alias = str(tree.children[0])
        agg_func_tree = tree.children[1]
    else:
        alias = None
        agg_func_tree = tree.children[0]

    return _build_agg_func(agg_func_tree, alias)


def _build_agg_func(tree: Tree, alias):
    dispatch = {
        "agg_count":   lambda t, a: AggCount(alias=a),
        "agg_sum":     lambda t, a: AggSum(col=_build_expr(t.children[0]), alias=a),
        "agg_avg":     lambda t, a: AggAvg(col=_build_expr(t.children[0]), alias=a),
        "agg_min":     lambda t, a: AggMin(col=_build_expr(t.children[0]), alias=a),
        "agg_max":     lambda t, a: AggMax(col=_build_expr(t.children[0]), alias=a),
        "agg_dcount":  lambda t, a: AggDCount(col=_build_expr(t.children[0]), alias=a),
        "agg_countif": lambda t, a: AggCountIf(
            condition=_build_bool_expr(t.children[0]), alias=a
        ),
        "agg_bin": lambda t, a: AggCount(alias=a),
        "agg_percentile": lambda t, a: AggPercentile(
            col=_build_expr(t.children[0]), percentile=_build_expr(t.children[1]), alias=a
        ),
        "agg_make_list": lambda t, a: AggMakeList(
            col=_build_expr(t.children[0]), alias=a
        ),
        "agg_stdev": lambda t, a: AggAvg(col=FuncCall(name="stddev", args=[_build_expr(t.children[0])]), alias=a),
    }
    builder = dispatch.get(tree.data)
    if builder is None:
        raise NotImplementedError(f"Unknown agg function: {tree.data}")
    return builder(tree, alias)


def _build_groupby_list(tree: Tree) -> list:
    """Note: Logic moved to _build_summarize to handle re-aliasing."""
    return []


def _build_order(tree: Tree) -> OrderOp:
    order_list = tree.children[0]
    items = []
    for item in order_list.children:
        if isinstance(item, Tree) and item.data == "order_item":
            col = _build_expr(item.children[0])
            direction = "asc"
            for tok in item.children[1:]:
                if isinstance(tok, Token) and str(tok).lower() in ("asc", "desc"):
                    direction = str(tok).lower()
            items.append(OrderItem(col=col, direction=direction))
    return OrderOp(items=items)


def _build_take(tree: Tree) -> TakeOp:
    n = int(str(tree.children[0]))
    return TakeOp(n=n)


def _build_distinct(tree: Tree) -> DistinctOp:
    if not tree.children:
        return DistinctOp(columns=[], star=True)
    for child in tree.children:
        if isinstance(child, Token) and str(child) == "*":
            return DistinctOp(columns=[], star=True)
    col_list = tree.children[0]
    return DistinctOp(
        columns=[str(t) for t in col_list.children if isinstance(t, Token)]
    )


def _build_extend(tree: Tree) -> ExtendOp:
    assign_list = tree.children[0]
    assignments = []
    for item in assign_list.children:
        if isinstance(item, Tree) and item.data == "assign_item":
            name = str(item.children[0])
            val_node = item.children[1]
            if isinstance(val_node, Tree):
                if val_node.data == "assign_comparison":
                    left = _build_expr(val_node.children[0])
                    op = str(val_node.children[1])
                    right = _build_expr(val_node.children[2])
                    expr = Comparison(left=left, op=op, right=right)
                else:
                    expr = _build_expr(val_node.children[0])
            else:
                expr = _build_expr(val_node)
            assignments.append((name, expr))
    return ExtendOp(assignments=assignments)


def _build_join(tree: Tree) -> JoinOp:
    kind = "inner"
    right_query = None
    keys = []

    for child in tree.children:
        if isinstance(child, Tree):
            if child.data == "join_kind":
                kind = str(child.children[-1])
            elif child.data == "table_expr":
                right_table = str(child.children[0])
                right_query = KQLQuery(table=right_table, pipes=[])
            elif child.data == "join_keys":
                keys = [str(t) for t in child.children if isinstance(t, Token)]

    if right_query is None:
        raise ValueError("join_op has no right-side table expression")

    return JoinOp(right=right_query, keys=keys, kind=kind)


def _build_union(tree: Tree) -> UnionOp:
    union_tables = tree.children[0]  # union_tables Tree
    tables = []       # simple table names
    subqueries = {}   # {table_name: KQLQuery} for subquery items

    for item in union_tables.children:
        if not isinstance(item, Tree):
            continue
        if item.data == 'union_table_name':
            tables.append(str(item.children[0]))
        elif item.data == 'union_table_subquery':
            ref = item.children[0]  # table_ref_expr
            sub = _build_table_ref(ref)
            # Use the subquery table name as key
            tables.append(sub.table)
            subqueries[sub.table] = sub

    return UnionOp(tables=tables, subqueries=subqueries)


# ─── BOOLEAN EXPRESSIONS ─────────────────────────────────────────────────────

def _build_bool_expr(tree) -> object:
    if isinstance(tree, Token):
        return Comparison(left=ColumnRef(str(tree)), op="==", right=BoolLit(True))

    if tree.data == "logical":
        left = _build_bool_expr(tree.children[0])
        op = str(tree.children[1]).lower()
        right = _build_bool_expr(tree.children[2])
        return LogicalOp(left=left, op=op, right=right)

    if tree.data == "negation":
        return Negation(expr=_build_bool_expr(tree.children[0]))

    if tree.data == "paren_bool":
        return _build_bool_expr(tree.children[0])

    if tree.data == "comparison":
        left = _build_expr(tree.children[0])
        comp_op_node = tree.children[1]
        if isinstance(comp_op_node, Tree):
            op = str(comp_op_node.children[0])
        else:
            op = str(comp_op_node)
        right = _build_expr(tree.children[2])
        return Comparison(left=left, op=op, right=right)

    if tree.data == "in_expr":
        col = _build_expr(tree.children[0])
        values = [_build_expr(v) for v in tree.children[1].children
                  if isinstance(v, Tree)]
        return InExpr(col=col, values=values, negated=False)

    if tree.data == "not_in_expr":
        col = _build_expr(tree.children[0])
        values = [_build_expr(v) for v in tree.children[1].children
                  if isinstance(v, Tree)]
        return InExpr(col=col, values=values, negated=True)

    if tree.data == "in_ci_expr":
        col = _build_expr(tree.children[0])
        values = [_build_expr(v) for v in tree.children[1].children
                  if isinstance(v, Tree)]
        return InExpr(col=col, values=values, negated=False, case_insensitive=True)

    if tree.data == "not_in_ci_expr":
        col = _build_expr(tree.children[0])
        values = [_build_expr(v) for v in tree.children[1].children
                  if isinstance(v, Tree)]
        return InExpr(col=col, values=values, negated=True, case_insensitive=True)

    if tree.data == "subquery_in_expr":
        col = _build_expr(tree.children[0])
        ref = tree.children[1]  # table_ref_expr Tree
        subquery = _build_table_ref(ref)
        return SubqueryInExpr(col=col, subquery=subquery, negated=False)

    if tree.data == "subquery_not_in_expr":
        col = _build_expr(tree.children[0])
        ref = tree.children[1]
        subquery = _build_table_ref(ref)
        return SubqueryInExpr(col=col, subquery=subquery, negated=True)

    if tree.data == "subquery_in_ci_expr":
        col = _build_expr(tree.children[0])
        ref = tree.children[1]
        subquery = _build_table_ref(ref)
        return SubqueryInExpr(col=col, subquery=subquery, negated=False, case_insensitive=True)

    if tree.data == "subquery_not_in_ci_expr":
        col = _build_expr(tree.children[0])
        ref = tree.children[1]
        subquery = _build_table_ref(ref)
        return SubqueryInExpr(col=col, subquery=subquery, negated=True, case_insensitive=True)

    if tree.data in ("has_expr", "contains_expr", "startswith_expr",
                     "endswith_expr", "regex_expr"):
        op_name = tree.data.replace("_expr", "").replace("_", " ")
        col = _build_expr(tree.children[0])
        value = _strip_quotes(str(tree.children[1]))
        return StringOp(col=col, op=op_name, value=value)

    if tree.data == "has_any_expr":
        col = _build_expr(tree.children[0])
        values = [_build_expr(v) for v in tree.children[1].children
                  if isinstance(v, Tree)]
        return HasAnyExpr(col=col, values=values)

    if tree.data == "between_expr":
        # Desugar between(expr .. expr) -> (col >= start) and (col <= end)
        col = _build_expr(tree.children[0])
        start = _build_expr(tree.children[1])
        end = _build_expr(tree.children[2])
        return LogicalOp(
            left=Comparison(left=col, op=">=", right=start),
            op="and",
            right=Comparison(left=col, op="<=", right=end)
        )

    if tree.data == "isnotnull_expr":
        return NullCheck(col=_build_expr(tree.children[0]), is_null=False)

    if tree.data == "isnull_expr":
        return NullCheck(col=_build_expr(tree.children[0]), is_null=True)

    if len(tree.children) == 1:
        return _build_bool_expr(tree.children[0])

    raise NotImplementedError(f"Unknown bool expr: {tree.data}")


# ─── SCALAR EXPRESSIONS ──────────────────────────────────────────────────────

def _build_expr(tree) -> object:
    if isinstance(tree, Token):
        return _token_to_expr(tree)

    if tree.data == "column_ref":
        return ColumnRef(name=str(tree.children[0]))

    if tree.data == "ago_expr":
        amount, unit = _build_timespan(tree.children[0])
        return AgoExpr(amount=amount, unit=unit)

    if tree.data == "bin_expr":
        col = _build_expr(tree.children[0])
        amount, unit = _build_timespan(tree.children[1])
        return BinExpr(col=col, amount=amount, unit=unit)

    if tree.data == "func_call":
        name = str(tree.children[0])
        args = [_build_expr(c) for c in tree.children[1:]
                if isinstance(c, Tree)]
        return FuncCall(name=name, args=args)

    if tree.data in ("add", "sub", "mul", "div"):
        left = _build_expr(tree.children[0])
        op = {"add": "+", "sub": "-", "mul": "*", "div": "/"}[tree.data]
        right = _build_expr(tree.children[1])
        return BinaryOp(left=left, op=op, right=right)

    if tree.data == "paren_expr":
        return _build_expr(tree.children[0])

    if tree.data == "string_lit":
        return StringLit(value=_strip_quotes(str(tree.children[0])))
    if tree.data == "int_lit":
        return IntLit(value=int(str(tree.children[0])))
    if tree.data == "float_lit":
        return FloatLit(value=float(str(tree.children[0])))
    if tree.data == "bool_lit":
        return BoolLit(value=str(tree.children[0]).lower() == "true")
    if tree.data == "datetime_lit":
        return DatetimeLit(raw=str(tree.children[0]))

    if tree.data == "iff_call":
        condition = _build_bool_expr(tree.children[0])
        true_val = _build_expr(tree.children[1])
        false_val = _build_expr(tree.children[2])
        return IffExpr(condition=condition, true_val=true_val, false_val=false_val)

    if len(tree.children) == 1:
        return _build_expr(tree.children[0])

    raise NotImplementedError(f"Unknown expr node: {tree.data}")


def _token_to_expr(token: Token) -> object:
    s = str(token)
    if s.startswith(("'", '"')):
        return StringLit(value=_strip_quotes(s))
    if s.lower() in ("true", "false"):
        return BoolLit(value=s.lower() == "true")
    try:
        return IntLit(value=int(s))
    except ValueError:
        pass
    try:
        return FloatLit(value=float(s))
    except ValueError:
        pass
    return ColumnRef(name=s)


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _build_table_ref(tree: Tree) -> object:
    """Build a KQLQuery from a table_ref_expr tree (used in let and in-subquery)."""
    table = str(tree.children[0])
    pipes = [_build_pipe_op(c) for c in tree.children[1:]
             if isinstance(c, Tree) and c.data == "pipe_op"]
    return KQLQuery(table=table, pipes=pipes, let_bindings=[])

def _build_timespan(tree: Tree) -> tuple[int, str]:
    """Returns (amount: int, kql_unit: str) e.g. (24, 'h')"""
    amount = int(str(tree.children[0]))
    unit = str(tree.children[1])
    return amount, unit


def _strip_quotes(s: str) -> str:
    if len(s) >= 2 and s[0] in ("'", '"') and s[-1] == s[0]:
        return s[1:-1]
    return s
