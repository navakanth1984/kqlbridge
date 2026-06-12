## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.
## 2023-10-27 - Fast String Parsing Optimization
**Learning:** In Python parsing logic, using an `enumerate` loop to track indices and perform string slicing (`string[start:i]`) is significantly faster than building a list character-by-character (`current.append(c)`) and joining it (`"".join(current)`). This avoids O(N) list allocations per token and can outperform complex `re.finditer()` logic for nested token parsing.
**Action:** Replace `while` loop character append/join loops with `enumerate` loops tracking indices when building parsers for nested KQL functions like `case()` or when breaking down expressions.
