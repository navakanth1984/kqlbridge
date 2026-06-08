import re
from kqlbridge.parser import _preprocess_case, _split_case_args, _build_iff_chain

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

def _preprocess_case_optimized(kql: str) -> str:
    pattern = re.compile(r"\bcase\b\s*\(", re.IGNORECASE)

    while True:
        match = pattern.search(kql)
        if not match:
            break

        start_idx = match.start()
        open_paren_idx = match.end() - 1

        paren_depth = 0
        close_paren_idx = -1

        for token_match in _CASE_ARGS_TOKEN_RE.finditer(kql, open_paren_idx):
            token_type = token_match.lastgroup
            if token_type == 'lparen':
                paren_depth += 1
            elif token_type == 'rparen':
                paren_depth -= 1
                if paren_depth == 0:
                    close_paren_idx = token_match.start()
                    break

        if close_paren_idx == -1:
            break

        arg_str = kql[open_paren_idx + 1:close_paren_idx]
        arg_str_rewritten = _preprocess_case_optimized(arg_str)
        args = _split_case_args(arg_str_rewritten)
        iff_chain = _build_iff_chain(args)

        kql = kql[:start_idx] + iff_chain + kql[close_paren_idx + 1:]

    return kql

test_str = "DeviceEvents | extend Risk = case(ActionType == 'Logon', 1, ActionType == 'Logoff', 0, ActionType == 'ProcessCreated', case(InitiatingProcessFileName == 'cmd.exe', 2, 0), 0)"
print(_preprocess_case(test_str))
print(_preprocess_case_optimized(test_str))
print(_preprocess_case(test_str) == _preprocess_case_optimized(test_str))
