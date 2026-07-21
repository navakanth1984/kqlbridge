## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.

## 2024-05-18 - String Building Loops vs String Slicing
**Learning:** In Python, appending characters to a list one-by-one (`current.append(c)`) and then calling `"".join(current)` inside a parsing loop is significantly slower than tracking index boundaries and using native string slicing (`string[start_idx:i]`). This is because the list approach allocates memory for every single character and requires additional function call overhead.
**Action:** When optimizing manual tokenization or parsing loops, prefer maintaining a `start_idx` and slicing out chunks directly from the original string.

## 2024-05-18 - O(N^2) Regex Rescanning in Iterative Replacement
**Learning:** Using `while True: match = pattern.search(string)` to repeatedly find and replace patterns causes O(N^2) behavior because the regex engine starts scanning from index 0 on every loop iteration, even though the previously matched portions haven't changed.
**Action:** Always maintain a `start_search` offset and pass it to the regex engine: `pattern.search(string, start_search)`. Advance the offset to `match.end()` on failure or to the start of the replacement on success to achieve O(N) performance. Ensure it correctly skips malformed patterns to avoid silent drops.
