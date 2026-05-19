## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.
<<<<<<< Updated upstream

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.
=======
## 2024-05-18 - Fix ExtendOp and UnionOp handling in SparkSQLGenerator
**Learning:** Spark SQL can reference column aliases directly in subsequent clauses without needing subqueries, and `UnionOp` needs to assemble the preceding pipe operators before combining tables, to maintain structural equivalence. Also, do not hardcode workaround for buggy test cases, as the score of 99.2% is already above target.
**Action:** Assemble KQL pipe ops before handling operators like `union` that combine sources. Avoid artificial subquery wrapping if the target SQL dialect can reference aliases.
>>>>>>> Stashed changes
