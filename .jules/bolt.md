## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.

## 2026-05-18 - Fast-pathing Python `try...except` in parsers
**Learning:** Using `try...except ValueError` for type casting control flow (like `int(s)` or `float(s)`) is extremely slow in Python when the exception is expected to happen frequently (e.g., standard identifiers failing numeric parsing).
**Action:** Implement a fast path by checking `s[0].isalpha() or s[0] == "_"` to immediately bypass numeric parsing for standard identifiers, but ensure edge cases like `"inf"`, `"nan"`, and `"infinity"` are caught and allowed to fallback to `float()`.
