## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.
## 2024-05-19 - Optimize boolean function parsing with pre-compiled regex and pos parameter
**Learning:** The `_preprocess_bool_funcs` iteratively sliced strings inside a parenthetical parsing loop to check if comparison operators (like `==`, `in`, `!in`) were present. The `!in` check failed because `!in` was mapped against a string splitting array using `\b`, which fails on `!` as it is a non-word character. Combining all checks into a single regex and using `.match(kql, pos)` reduced execution time for this stage from ~2.7s to ~0.9s per 100k iterations and fixed the `!in` bug, demonstrating that relying on `.match` with `pos` is heavily preferred to string slice logic.
**Action:** Always precompile heavily used regexes containing multiple OR conditions and utilize `pattern.match(string, index)` instead of iterating through arrays of checks and slicing strings within hot parsing loops.
