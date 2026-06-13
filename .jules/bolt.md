## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.
## 2026-06-13 - Enumerate vs re.finditer in Nested Parsers
**Learning:** When parsing simple nested structures (e.g. keeping track of parentheses depths while skipping quotes) in Python, avoiding O(N) array allocations via `current.append(c)` and `"".join(current)` can yield immediate speedups without reaching for complex regexes. Switching to `enumerate` and tracking start/end pointers to `append(string[start:i])` can be faster than `re.finditer` because it minimizes object overhead.
**Action:** When refactoring character-by-character parsers for speed, test an index/slicing approach before switching to `re.finditer()`, especially when logic involves state tracking (paren depth) rather than direct text substitution.
