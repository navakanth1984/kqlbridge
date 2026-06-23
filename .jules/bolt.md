## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.
## 2024-06-23 - Python String Building Loops vs Slicing
**Learning:** When optimizing Python string building loops (e.g. `current.append(c)` and `"".join(current)`), replacing them with an index tracking loop and using native string slicing (e.g. `string[start_idx:i]`) is faster and avoids O(N) list allocations per token. This can even outperform complex `re.finditer()` tokenizers for simple nested token parsing in Python.
**Action:** When parsing simple nested structures, use a `start_idx` pointer and index slicing over allocating arrays of single characters.

## 2024-06-23 - O(N²) regex scanning
**Learning:** When optimizing iterative string search-and-replace routines (e.g., in a `while` loop), failing to maintain a search index offset and pass it to `re.search(pattern, start_search)` can cause O(N²) rescanning from index 0. If the routine handles nested structures (like KQL `case` statements), advance `start_search` to `match.start()` instead of skipping the entire replacement length to ensure inner or subsequent tokens are not mistakenly bypassed.
**Action:** Always use the `pos` or `start_search` parameter when repeatedly applying a regex over a large string to ensure linear time complexity.
