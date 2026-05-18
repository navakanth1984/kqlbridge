## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2024-05-18 - String Normalization Optimization in Parser
**Learning:** Manual character-by-character while loops performing `re.match` on substrings in Python are extremely slow. They dominate parsing execution time.
**Action:** Always prefer vectorized operations like `re.sub` with a combined pre-compiled regex pattern instead of manual string parsing loops in Python.
