## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.
## 2026-05-18 - String building and regex scanning O(N^2) bottlenecks
**Learning:** Character-by-character string building using list appends and `"".join(current)` is slow due to memory allocation overhead. Additionally, calling `pattern.search(string)` inside a loop without an index tracks causes the engine to re-scan the entire string from index 0 on every pass (O(N^2) complexity).
**Action:** Use native string slicing (e.g. `string[start_idx:i]`) instead of list appends for token generation. When doing iterative regex searches, track the current position (e.g. `search_idx = match.start()`) and use `pattern.search(string, search_idx)` to resume parsing without rescanning.
