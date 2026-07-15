## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.

## 2026-07-15 - Iterative String Search and Replace Loops
**Learning:** In iterative string parsing/replacement loops, when encountering malformed syntax (e.g., an unclosed parenthesis), advancing the search index past the current match (e.g., `start_search = match.end()`) and continuing rather than using `break` makes the parser more robust. It ensures that subsequent valid patterns later in the string are still correctly processed.
**Action:** Use `continue` with an advanced index instead of `break` when encountering isolated syntax errors in recursive string scanners.
