## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.
## 2026-05-31 - String Slicing Over List Appending
**Learning:** When optimizing Python string building loops (e.g. `current.append(c)` and `"".join(current)`), replacing them with an index tracking loop and using native string slicing (e.g. `string[start_idx:i]`) is faster and avoids O(N) list allocations per token. This can even outperform complex `re.finditer()` tokenizers for simple nested token parsing in Python.
**Action:** When refactoring hand-written parsers in Python that accumulate strings character-by-character, always prefer index-tracking and native string slicing.
