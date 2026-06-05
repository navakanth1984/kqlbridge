## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.

## 2024-06-05 - Bulk matching vs Character matching in Regex Token Scans
**Learning:** When using `re.finditer` to optimize a character-by-character `while` loop (like a parser or tokenizer), relying entirely on single-character fallbacks (e.g., `.` or single structural tokens like `\(`, `\,`) can actually make the regex approach slower than a simple Python loop. To unlock the C-engine speedup, the regex must include a "bulk match" group (e.g., `[^'",()]+`) that aggressively consumes all non-structural characters in a single operation.
**Action:** Always include a negated character class to bulk-consume non-special text before the final `.` fallback token when designing regex token scanners for performance.
