## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.

## 2026-05-18 - Character-by-Character String Parsing Bottleneck
**Learning:** Python `while` or `for` loops that iterate character-by-character over a string to match parentheses and track state (e.g. quote status) are extremely slow for large inputs, exhibiting O(N) traversal overhead with high Python loop cost.
**Action:** Replace manual state-tracking character loops with C-optimized regex tokenizers (e.g. using `re.finditer(pattern, string)`) to scan tokens. Always include a fallback token (like `r'.'`) at the end of the regex to safely consume malformed or arbitrary intermediate inputs without getting stuck or skipping tokens.
