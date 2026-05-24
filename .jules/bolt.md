## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.

## 2026-05-24 - O(N) Character-by-Character Parsing loops
**Learning:** Character-by-character string parsing using manual `while` loops and tracking state (like `paren_depth` and `in_single_quote`) in Python is significantly slower than using compiled C-backed regexes (`re.finditer`) to tokenize string literals and parens, due to the interpreter overhead for each character.
**Action:** Replace manual character-by-character loops with regex tokenization using `re.finditer` when looking for specific boundaries (like finding balancing parentheses outside of quotes) in KQL normalizers.
