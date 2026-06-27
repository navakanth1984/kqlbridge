## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.

## 2026-05-18 - String Building Loops vs Index Slicing
**Learning:** In Python, replacing character-by-character string building loops (using `current.append(c)` and `"".join(current)`) with index tracking and native string slicing (`string[start_idx:i]`) can be a significant optimization. It avoids O(N) list allocations per token and outperforms complex `re.finditer()` tokenizers for simple string tracking logic.
**Action:** Always prefer native index tracking and slicing over iterative array building when extracting substrings in linear passes.
