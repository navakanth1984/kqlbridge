## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.
## 2026-05-18 - re.finditer vs String Index Loops
**Learning:** Python's C-optimized `re` module (`re.finditer`) drastically outperforms Python-level character iteration `while` or `for` loops for string parsing/tokenizing. Extracting string tokens via regex and using generator methods is about ~30% faster for short queries and ~2-3x faster for long sequences than manual array string slicing.
**Action:** Replace `while i < len(string)` looping constructs that check single characters with combined regex pattern tokenization (`re.finditer`) inside python string manipulation functions.
