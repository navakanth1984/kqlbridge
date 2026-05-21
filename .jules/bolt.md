## 2026-05-21 - Optimize character-by-character loops using RegEx
**Learning:** Python string iteration character-by-character `while` loops in parsing code (e.g., `_split_case_args`, `_preprocess_case`) are extremely slow and have O(N^2) complexity with `len(kql)`. Recursive iff-chains easily hit `RecursionError`.
**Action:** Replace manual state management parsing loops with pre-compiled regex and `re.finditer` to jump through tokens (quotes, parens). Replace deep string concatenation recursion with iterative backwards evaluation (`reversed(pairs)`) to ensure safety and massive speedups.
