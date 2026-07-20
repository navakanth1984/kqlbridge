## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.

## 2024-05-18 - ValueError Exception Overhead in Parsers
**Learning:** Using `try...except ValueError` for type-casting as a form of control flow (e.g., checking if an identifier string is a float/int by running `float(s)`) is extremely slow in Python when the exception is expected frequently, which happens often in parsers reading standard identifiers (like column names).
**Action:** Implement a fast path to avoid the exception completely. For example, if checking standard identifiers, check if the string starts with an alphabetical character or underscore (`s[0].isalpha() or s[0] == '_'`) before attempting `float()` or `int()` conversions. Always remember to account for edge cases like `'inf'`, `'nan'`, and `'infinity'` which *do* parse as valid floats!
