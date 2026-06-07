## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.

## 2024-05-30 - C-Optimized Token Scanning Replaces Python `while` Loops for Parsing Speedup
**Learning:** Native Python character-by-character loops are extremely slow for string parsing. By replacing standard `while i < len(str)` loops and manual state management (like quote flags) with C-optimized regex `re.finditer()` token scanners, we can achieve nearly 2x performance improvements without losing parsing fidelity, as long as backslashes inside string tokens are safely handled.
**Action:** When parsing strings containing nested tokens (e.g. parenthesis and commas) while preserving quoted literals, pre-compile a regex tokenizing pattern (`r"""'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*"|[()]|[^'",()]+|."""`) and iterate over `finditer` matches rather than single characters.
