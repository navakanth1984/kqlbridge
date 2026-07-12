## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.

## 2026-05-18 - Fast-pathing expensive try/except parsing
**Learning:** Using `try...except ValueError` for type-casting as control flow (e.g., checking if an identifier string is a float/int) is extremely slow in Python when the exception is expected frequently, which is typical for standard parsing.
**Action:** Implementing a fast path (e.g., checking if the string starts with an alphabetical character) avoids this significant overhead. However, always ensure valid alphabetical keywords for that type (like `inf`, `nan` for floats) are handled.

## 2026-05-18 - List append vs String slicing
**Learning:** When building substrings inside a parsing loop, appending characters to a list `current` and eventually calling `"".join(current)` incurs a measurable overhead due to `O(N)` list allocations and memory re-allocations per token.
**Action:** Tracking indices (`start_idx` and `i`) and using native string slicing (`string[start_idx:i]`) natively bypasses these multiple list re-allocations and improves parsing speed, outperforming character-by-character list aggregation.
