## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.

## 2024-05-18 - Replacing O(N) string loops with finditer
**Learning:** Manual character-by-character loops parsing string tokens are significantly slower than letting Python's underlying C engine perform the matching using `re.finditer` with pre-compiled regex tokens.
**Action:** When manually parsing tokens like strings, parens, and generic content, use `_re.compile(..., _re.DOTALL)` with string literals capturing backslashes (`r"'(?:[^'\\]|\\.)*'|..."`) and end it with `|.` to gracefully fallback instead of looping over string indices.
