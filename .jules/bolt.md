## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.

## 2026-05-18 - Optimized parsing loops
**Learning:** In Python, tracking a search index for regex `search()` and utilizing string slicing `str[start_idx:i]` avoids the O(N^2) complexity of slicing on each iteration and the overhead of list `.append()` with `"".join()`. This is particularly useful for loops implementing tokenizers or character scanners.
**Action:** Always prefer maintaining an index offset `pattern.search(string, start_index)` and string slicing (`str[start:end]`) over allocating temporary lists and slicing per iteration (`str[i:]`) in parser functions.
