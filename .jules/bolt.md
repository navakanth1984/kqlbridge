## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.
## 2026-05-17 - Pre-Processing Boolean Functions `to_bool()` Injection Logic
**Learning:** The legacy replacement logic for boolean functions (`ipv4_is_private`, `ipv4_is_in_range`) used string splicing and manually appended ` == true` when it was not part of a comparison. However, my initial regex iteration blindly replaced it with a wrapper `to_bool(...)`. Since `to_bool` isn't a supported grammar operator in kqlbridge, it threw `Unexpected end-of-input` during Lark parsing.
**Action:** When replacing text-manipulating code, you must perfectly preserve the generated code text shape unless you are purposefully extending the grammar in `.lark`. Reverted to preserving the original ` == true` suffix check using the pre-compiled `_BOOL_COMP_RE` rather than attempting a more "readable" `to_bool()` translation.
