## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.

## 2026-05-31 - O(N^2) Rescanning in Search-and-Replace Loops
**Learning:** Using `while True: match = pattern.search(string)` without tracking a `start_search` index causes Python's regex engine to rescan the entire string from index 0 on every iteration. This leads to severe O(N^2) bottlenecks when replacing multiple matches, such as nested `case` statements in KQL.
**Action:** When implementing iterative string search-and-replace routines, always maintain a search index offset and pass it to `re.search(pattern, start_search)`. If handling nested structures, advance `start_search` to `match.start()` instead of `match.end()` to ensure inner or subsequent matches dynamically added are properly caught.
