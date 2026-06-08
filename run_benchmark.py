import re
import timeit

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


test_str1 = "ActionType == 'Logon', 1, ActionType == 'Logoff', 0, ActionType == 'ProcessCreated', case(InitiatingProcessFileName == 'cmd.exe', 2, 0), 0"
test_str_large = test_str1 * 10

print("Testing _split_case_args (short)...")
t1 = timeit.timeit("_split_case_args(test_str1)", globals=globals(), number=10000)
t2 = timeit.timeit("_split_case_args_optimized(test_str1)", globals=globals(), number=10000)
print(f"Original: {t1:.4f}s")
print(f"Optimized: {t2:.4f}s")
print(f"Speedup: {t1/t2:.2f}x\n")

print("Testing _split_case_args (large)...")
t1 = timeit.timeit("_split_case_args(test_str_large)", globals=globals(), number=1000)
t2 = timeit.timeit("_split_case_args_optimized(test_str_large)", globals=globals(), number=1000)
print(f"Original: {t1:.4f}s")
print(f"Optimized: {t2:.4f}s")
print(f"Speedup: {t1/t2:.2f}x\n")

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

_BOOL_FUNCS_RE = re.compile(
    r"\b(has|has_cs|contains|contains_cs|startswith|startswith_cs|endswith|endswith_cs|matches\s+regex)\s*\(",
    re.IGNORECASE
)

_BOOL_COMP_RE = re.compile(r"\s*(==|!=|<>|>=|<=|>|<|=~|!~|\bin\b|!in\b|\bbetween\b)", re.IGNORECASE)

def _preprocess_bool_funcs(kql: str) -> str:
    i = 0
    while i < len(kql):
        match = _BOOL_FUNCS_RE.search(kql, i)
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

        if not _BOOL_COMP_RE.match(kql, close_paren_idx + 1):
            kql = kql[:close_paren_idx + 1] + " == true" + kql[close_paren_idx + 1:]
            i = close_paren_idx + 1 + len(" == true")
        else:
            i = close_paren_idx + 1
    return kql

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

test_str3 = "DeviceEvents | where ActionType == 'Logon' and (InitiatingProcessFileName in ('cmd.exe', 'powershell.exe') or has('Invoke-')) | extend is_evil = has('evil')"
test_str3_large = test_str3 * 10

print("Testing _preprocess_bool_funcs (short)...")
t1 = timeit.timeit("_preprocess_bool_funcs(test_str3)", globals=globals(), number=10000)
t2 = timeit.timeit("_preprocess_bool_funcs_optimized(test_str3)", globals=globals(), number=10000)
print(f"Original: {t1:.4f}s")
print(f"Optimized: {t2:.4f}s")
print(f"Speedup: {t1/t2:.2f}x\n")

print("Testing _preprocess_bool_funcs (large)...")
t1 = timeit.timeit("_preprocess_bool_funcs(test_str3_large)", globals=globals(), number=1000)
t2 = timeit.timeit("_preprocess_bool_funcs_optimized(test_str3_large)", globals=globals(), number=1000)
print(f"Original: {t1:.4f}s")
print(f"Optimized: {t2:.4f}s")
print(f"Speedup: {t1/t2:.2f}x\n")


def _preprocess_case(kql: str) -> str:
    pattern = re.compile(r"\bcase\b\s*\(", re.IGNORECASE)

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
        from kqlbridge.parser import _build_iff_chain
        args = _split_case_args(arg_str_rewritten)
        iff_chain = _build_iff_chain(args)

        kql = kql[:start_idx] + iff_chain + kql[close_paren_idx + 1:]

    return kql

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
        from kqlbridge.parser import _build_iff_chain
        args = _split_case_args_optimized(arg_str_rewritten)
        iff_chain = _build_iff_chain(args)

        kql = kql[:start_idx] + iff_chain + kql[close_paren_idx + 1:]

    return kql

test_str2 = "DeviceEvents | extend Risk = case(ActionType == 'Logon', 1, ActionType == 'Logoff', 0, ActionType == 'ProcessCreated', case(InitiatingProcessFileName == 'cmd.exe', 2, 0), 0)"
test_str2_large = test_str2 * 10

print("Testing _preprocess_case (short)...")
t1 = timeit.timeit("_preprocess_case(test_str2)", globals=globals(), number=5000)
t2 = timeit.timeit("_preprocess_case_optimized(test_str2)", globals=globals(), number=5000)
print(f"Original: {t1:.4f}s")
print(f"Optimized: {t2:.4f}s")
print(f"Speedup: {t1/t2:.2f}x\n")

print("Testing _preprocess_case (large)...")
t1 = timeit.timeit("_preprocess_case(test_str2_large)", globals=globals(), number=500)
t2 = timeit.timeit("_preprocess_case_optimized(test_str2_large)", globals=globals(), number=500)
print(f"Original: {t1:.4f}s")
print(f"Optimized: {t2:.4f}s")
print(f"Speedup: {t1/t2:.2f}x\n")
