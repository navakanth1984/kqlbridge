## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.
## 2023-10-24 - O(N^2) Rescanning Bug in Nested Logic

**Learning:** When optimizing iterative string search-and-replace routines (like `case` processing) with a `start_search` index to avoid O(N^2) rescanning, advancing the index strictly past the *newly inserted content* (e.g., `start_search = start_idx + len(new_content)`) will silently skip any nested operations inside that new content. In KQL, `case` statements can be deeply nested (e.g., `case(..., case(...), ...)`).

**Action:** Maintain a search index offset and pass it to `re.search(pattern, start_search)` to resume searching. Advance `start_search` to `match.start()` instead of skipping the entire replacement length to ensure inner or subsequent tokens are not mistakenly bypassed.
