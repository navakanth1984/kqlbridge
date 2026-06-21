## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.

## 2024-06-21 - O(N) Object Allocation in String Building Loops
**Learning:** Using `current.append(c)` and `"".join(current)` inside character-by-character parsing loops leads to significant overhead from continuous list resizing and single-character allocations. This bottleneck severely degrades performance for deeply nested KQL expressions like `case()`.
**Action:** Replace iterative list appending with index tracking (`start_idx`) and direct string slicing (`arg_str[start_idx:i]`). This avoids allocating intermediate memory structures and relies on native C-level operations in Python, yielding measurable speedup for deeply nested expressions.
