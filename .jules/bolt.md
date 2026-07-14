## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.

## 2026-05-18 - Exception Handling Overhead in Hot Paths
**Learning:** Using `try...except ValueError` for type-casting (e.g., `int(s)`, `float(s)`) inside a heavily-called function like `_token_to_expr` introduces massive overhead because exceptions in Python are expensive when caught frequently.
**Action:** Always implement a fast-path filter (e.g., checking if the first character `isalpha()` or is an underscore) before attempting expensive type casts that are expected to fail frequently (such as on column identifiers).
