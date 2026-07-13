## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.
## 2026-05-18 - Search loop state optimization
**Learning:** Using `regex.search(string)` from the beginning inside a `while True` replacement loop leads to O(N^2) complexity because the regex engine rescans the growing prefix string on every iteration.
**Action:** When performing iterative string replacement with regex (especially for nested structures like `case` in parsers), always track `start_search` and pass it via `regex.search(string, start_search)`. The index should be advanced to the start of the replacement rather than the end to ensure nested or overlapping subsequent matches are not skipped.
