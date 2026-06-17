## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.
## 2026-05-18 - Avoid String Slicing and .lower() Copies in Hot Loops
**Learning:** In Python, iterating over a string slice (`for j, c in enumerate(string[start:])`) creates a full memory copy of the substring, resulting in an O(M x N) performance/memory degradation in hot loops. Additionally, adding "fast-paths" that call `.lower()` on large strings (e.g., `if "keyword" not in query.lower():`) forces a full O(N) allocation that often negates any speedup over a C-optimized inplace `re.search`.
**Action:** When optimizing parsers, use index-based access (`for i in range(start, len(string)): c = string[i]`) instead of sliced iteration, and avoid full-string `.lower()` calls as fast-paths if an inplace regex search is already available.
