## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.

## 2024-07-22 - Fast pathing expensive try-except typecasts
**Learning:** Using `try...except ValueError` to check if a string token is an integer or float is an anti-pattern when parsing identifiers (like column names), because standard alphanumeric strings will always trigger the `ValueError`, which incurs significant Python VM overhead.
**Action:** When classifying tokens, add a fast path (`isalpha()` or `[0] == "_"`) to instantly resolve known string identifiers. Always ensure to special-case edge values that *can* be parsed as floats, such as `'inf'`, `'nan'`, and `'infinity'`.
