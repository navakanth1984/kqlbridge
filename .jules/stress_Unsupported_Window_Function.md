# FAILURE: Unsupported Window Function

**KQL:**
```kusto
SecurityEvents
| serialize
| extend prev_event = prev(event_id)
```

**Traceback:**
```python
Traceback (most recent call last):
  File "C:\Users\navka\navakanth001\kqlbridge\run_stress_test.py", line 159, in run
    engine, code = smart_transpile(kql.strip())
                   ~~~~~~~~~~~~~~~^^^^^^^^^^^^^
  File "C:\Users\navka\navakanth001\kqlbridge\src\kqlbridge\smart.py", line 29, in smart_transpile
    query = parse(kql)
  File "C:\Users\navka\navakanth001\kqlbridge\src\kqlbridge\parser.py", line 114, in parse
    tree = get_parser().parse(normalized)
  File "C:\Users\navka\AppData\Local\Programs\Python\Python313\Lib\site-packages\lark\lark.py", line 677, in parse
    return self.parser.parse(text, start=start, on_error=on_error)
           ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\navka\AppData\Local\Programs\Python\Python313\Lib\site-packages\lark\parser_frontends.py", line 131, in parse
    return self.parser.parse(stream, chosen_start, **kw)
           ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\navka\AppData\Local\Programs\Python\Python313\Lib\site-packages\lark\parsers\earley.py", line 280, in parse
    to_scan = self._parse(lexer, columns, to_scan, start_symbol)
  File "C:\Users\navka\AppData\Local\Programs\Python\Python313\Lib\site-packages\lark\parsers\xearley.py", line 153, in _parse
    to_scan, node_cache = scan(i, to_scan)
                          ~~~~^^^^^^^^^^^^
  File "C:\Users\navka\AppData\Local\Programs\Python\Python313\Lib\site-packages\lark\parsers\xearley.py", line 125, in scan
    raise UnexpectedCharacters(stream, i, text_line, text_column, {item.expect.name for item in to_scan},
    ...<2 lines>...
                               )
lark.exceptions.UnexpectedCharacters: No terminal matches 's' in the current parser context, at line 2 col 3

| serialize
  ^
Expected one of:
	* JOIN
	* SORT
	* WHERE
	* DISTINCT
	* COUNT
	* EXTEND
	* TAKE
	* ORDER
	* UNION
	* LIMIT
	* PROJECT
	* SUMMARIZE


```
