## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.

## 2024-06-20 - O(N^2) String Search in Loops
**Learning:** Using `re.search(pattern, string)` inside a `while` loop that iteratively modifies and searches a string causes O(N^2) behavior because the regex engine rescans the unmodified beginning of the string on every pass.
**Action:** Always maintain a `search_start` index and use `pattern.search(string, search_start)`. When modifying the string, advance `search_start` to `match.start()` to ensure subsequent inner patterns are still found, while safely bypassing the already processed prefix.

## 2024-06-20 - Native String Slicing > List Appends
**Learning:** When building strings conditionally character-by-character (like in token parsers that handle quotes and parens), replacing `current.append(c)` and `"".join(current)` with an index-tracking loop and native string slicing (`string[start:i]`) is significantly faster.
**Action:** Use native string slicing with `start` and `end` indices instead of character-by-character list building in hand-written parsers.
