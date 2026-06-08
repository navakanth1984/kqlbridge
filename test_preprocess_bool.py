import re
from kqlbridge.parser import _preprocess_bool_funcs

_BOOL_FUNCS_RE = re.compile(
    r"\b(has|has_cs|contains|contains_cs|startswith|startswith_cs|endswith|endswith_cs|matches\s+regex)\s*\(",
    re.IGNORECASE
)

_BOOL_COMP_RE = re.compile(r"\s*(==|!=|<>|>=|<=|>|<|=~|!~|\bin\b|!in\b|\bbetween\b)", re.IGNORECASE)

_PAREN_MATCH_RE = re.compile(
    r"""
    (?P<squote>'(?:[^'\\]|\\.)*') |
    (?P<dquote>"(?:[^"\\]|\\.)*") |
    (?P<lparen>\()                |
    (?P<rparen>\))                |
    (?P<text>[^'"()]+)            |
    (?P<fallback>.)
    """,
    re.VERBOSE
)

def _preprocess_bool_funcs_optimized(kql: str) -> str:
    i = 0
    while i < len(kql):
        match = _BOOL_FUNCS_RE.search(kql, i)
        if not match:
            break
        open_paren_idx = match.end() - 1
        paren_depth = 0
        close_paren_idx = -1

        for token_match in _PAREN_MATCH_RE.finditer(kql, open_paren_idx):
            token_type = token_match.lastgroup
            if token_type == 'lparen':
                paren_depth += 1
            elif token_type == 'rparen':
                paren_depth -= 1
                if paren_depth == 0:
                    close_paren_idx = token_match.start()
                    break

        if close_paren_idx == -1:
            i = open_paren_idx + 1
            continue

        if not _BOOL_COMP_RE.match(kql, close_paren_idx + 1):
            kql = kql[:close_paren_idx + 1] + " == true" + kql[close_paren_idx + 1:]
            i = close_paren_idx + 1 + len(" == true")
        else:
            i = close_paren_idx + 1
    return kql

test_str = "DeviceEvents | where ActionType == 'Logon' and (InitiatingProcessFileName in ('cmd.exe', 'powershell.exe') or InitiatingProcessCommandLine has 'Invoke-') | extend is_evil = InitiatingProcessCommandLine has 'evil'"
print(_preprocess_bool_funcs(test_str))
print(_preprocess_bool_funcs_optimized(test_str))
print(_preprocess_bool_funcs(test_str) == _preprocess_bool_funcs_optimized(test_str))
