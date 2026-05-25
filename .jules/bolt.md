## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.

## 2024-05-18 - Recursive AST Processing on Deep Pipelines
**Learning:** `kqlbridge` sometimes has deeply nested ast structures for functions like `case()` or deeply chained iff statements, and building this via recursive string manipulation or AST building causes `RecursionError` in Python around depths of 500-1000 due to Python's recursion limit.
**Action:** When building nested logical chains (like nested `iff`s), use iterative backward evaluation `reversed(pairs)` instead of recursion to prevent `RecursionError` on large input limits and improve execution speed by eliminating python function call overhead.
