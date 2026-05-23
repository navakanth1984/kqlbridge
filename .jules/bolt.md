## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.

## 2026-05-22 - RecursionError in Transpiler AST Builders
**Learning:** Building deeply nested logical chains (like `iff` functions or `case` statements) using recursion in the parser causes `RecursionError` in Python when evaluating large queries because it quickly exceeds Python's default recursion limit (1000). Recursive logic on AST node construction is a structural bottleneck.
**Action:** When evaluating chained inputs that need to be folded (e.g. nested fallback clauses), use iterative backward evaluation using a `for` loop rather than recursive calls.
