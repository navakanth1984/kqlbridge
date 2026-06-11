## 2026-05-17 - Lark Parser Import Bottleneck
**Learning:** Initializing the Lark parser synchronously during module import takes a significant amount of time (~50-100ms) because it parses the grammar file from disk. This slows down any script or agent importing the package, even if it doesn't parse any query.
**Action:** Always lazy-load heavy parsers (like Lark) behind a getter function when they are bound to a module-level variable.

## 2026-05-17 - O(N^2) String Slicing in Parsers
**Learning:** Using `re.match(pattern, string[i:])` inside a loop for parsing or lexing causes O(N^2) behavior due to string slicing on every iteration. This is a common performance bottleneck in hand-written lexers/normalizers.
**Action:** Always pre-compile regex patterns and use the `pos` parameter: `pattern.match(string, i)` to match at an index without creating a new string slice.

## 2026-06-11 - Regex Tokenization vs String Slicing
**Learning:** For hand-written tokenizers handling complex nested state (like parsing KQL `case` arguments that deal with quotes and parentheses depth), a pure python loop doing character appends (`current.append(c)`) is slow. While `re.finditer()` with a tokenizer regex avoids the python-level character loop, an `enumerate` loop tracking start indices and yielding slices (`string[start:i]`) is often ~30-50% faster in Python because it completely avoids regex overhead and temporary array allocations.
**Action:** When refactoring character-by-character string building loops, prefer `enumerate` + string slicing over `re.finditer` tokenization if the parsing state machine is simple enough.
