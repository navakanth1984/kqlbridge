## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.

## 2026-05-18 - Fast String Slicing vs Array Appends
**Learning:** When building strings character by character in a parser loop, using `current.append(c)` and `"".join(current)` incurs significant overhead from constant list allocations. Using native string slicing `string[start_idx:end_idx]` is significantly faster in Python.
**Action:** Replace `"".join(list)` with index tracking and string slicing when parsing linear tokens.

## 2026-05-18 - O(N^2) Repeated Search Operations
**Learning:** Calling `re.search(pattern, text)` in a `while` loop, performing a replacement, and looping without passing a `pos` index causes the regex engine to rescan the entire prefix of the string from index 0 on every iteration, leading to O(N^2) complexity on large inputs.
**Action:** Maintain a `search_start` index variable. When replacing text, advance `search_start` to `match.start()` to avoid rescanning the prefix while safely allowing inner nested tokens to be parsed.
