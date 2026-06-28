## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.

## 2026-05-17 - O(N^2) String Slicing and Search loops in Parsing
**Learning:** Using `"".join(current)` and array-building loops byte-by-byte (`current.append(c)`) in Python is significantly slower than traversing indices and capturing a final string slice (`string[start:end]`). Also, using `re.search()` inside a `while True` loop that mutates a string creates O(N^2) behavior because it rescans from index 0 every loop iteration.
**Action:** Replace `while` loop index byte-building with slicing based on tracked index positions. Always pass the `start_search` index parameter to `re.search(pattern, string, start_search)` to keep performance bounded to O(N).
