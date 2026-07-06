## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.

## 2026-05-18 - Cost of Exception Handling in Python Parsing
**Learning:** Using `try...except ValueError` for type-casting as control flow (like checking if a string is a float/int) is extremely slow in Python when the exception is expected frequently (e.g., parsing common identifiers in KQL). For large query payloads, catching these exceptions adds massive overhead.
**Action:** Implementing a fast path (e.g., checking if the string starts with an alphabetical character to early-return an identifier) avoids this overhead entirely. Always consider the frequency of the exception path when relying on duck-typing typecasts.
