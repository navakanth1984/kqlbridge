## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.

## 2024-05-18 - Fast-path bypassing exception control flow
**Learning:** Using `try...except ValueError` for type-casting as a form of control flow (e.g., checking if a string can be parsed as a float/int) is extremely slow in Python when exceptions are expected frequently, which is true when parsing typical text tokens (most are alphabetic column references).
**Action:** Implementing a fast path (e.g., checking `isalpha()` or `_`) avoids the substantial overhead of raising and catching exceptions in hot parsing paths.
