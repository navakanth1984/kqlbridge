import re
from kqlbridge.parser import _split_case_args

_CASE_ARGS_TOKEN_RE = re.compile(
    r"""
    (?P<squote>'(?:[^'\\]|\\.)*') |
    (?P<dquote>"(?:[^"\\]|\\.)*") |
    (?P<lparen>\()                |
    (?P<rparen>\))                |
    (?P<comma>,)                  |
    (?P<text>[^'",()]+)           |
    (?P<fallback>.)
    """,
    re.VERBOSE
)

def _split_case_args_optimized(arg_str: str) -> list[str]:
    args = []
    current = []
    paren_depth = 0

    for match in _CASE_ARGS_TOKEN_RE.finditer(arg_str):
        token = match.group(0)
        token_type = match.lastgroup

        if token_type == 'lparen':
            paren_depth += 1
            current.append(token)
        elif token_type == 'rparen':
            paren_depth -= 1
            current.append(token)
        elif token_type == 'comma' and paren_depth == 0:
            args.append("".join(current).strip())
            current.clear()
        else:
            current.append(token)

    if current:
        args.append("".join(current).strip())
    return args

test_str = "ActionType == 'Logon', 1, ActionType == 'Logoff', 0, ActionType == 'ProcessCreated', case(InitiatingProcessFileName == 'cmd.exe', 2, 0), 0" * 10
import timeit
print("Original:", timeit.timeit("from __main__ import _split_case_args, test_str; _split_case_args(test_str)", number=1000))
print("Optimized:", timeit.timeit("from __main__ import _split_case_args_optimized, test_str; _split_case_args_optimized(test_str)", number=1000))
