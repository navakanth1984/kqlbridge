## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.

## 2026-05-30 - O(N) String Parsing Bottleneck in Token Scanning
**Learning:** Manual character-by-character loops (e.g., `for i in range(len(s)): if s[i] == '(': ...`) in Python are significantly slower than letting the underlying C-based regex engine handle it. Using `re.finditer` with a tokenizing regex (e.g., matching string literals and specific punctuation) reduces evaluation time of deep token structures by ~40-50% and fixes edge cases (like proper backslash-escaping inside strings) at almost no complexity cost.
**Action:** When parsing structures like `case()` or tokenizing strings for function arguments in KQL, define a pre-compiled tokenizing regex (using named/unnamed groups) and iterate over tokens via `finditer` rather than slicing/indexing loops.
