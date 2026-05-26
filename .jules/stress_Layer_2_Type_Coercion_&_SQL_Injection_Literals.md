# FAILURE: Layer 2: Type Coercion & SQL Injection Literals

**KQL:**
```kusto
SecurityEvents
| extend int_max = 2147483647
| extend bigint_max = 9223372036854775807
| extend float_max = 1.7976931348623158
| extend sqli_classic = "' OR '1'='1"
| extend sqli_drop = '"; DROP TABLE users;--'
| extend tpli_probe = "${7*7}"
| project int_max, bigint_max, float_max, sqli_classic, sqli_drop, tpli_probe
```

**Traceback:**
```python
Traceback (most recent call last):
  File "C:\Users\navka\navakanth001\kqlbridge\run_stress_test.py", line 159, in run
    engine, code = smart_transpile(kql.strip())
                   ~~~~~~~~~~~~~~~^^^^^^^^^^^^^
  File "C:\Users\navka\navakanth001\kqlbridge\src\kqlbridge\smart.py", line 114, in smart_transpile
    return "pyspark", gen.generate(optimized_query)
                      ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
  File "C:\Users\navka\navakanth001\kqlbridge\src\kqlbridge\generators\pyspark.py", line 30, in generate
    lines.extend(self._generate_query(query, "df", let_names))
                 ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\navka\navakanth001\kqlbridge\src\kqlbridge\generators\pyspark.py", line 120, in _generate_query
    if pipe.aliases and col in pipe.aliases:
       ^^^^^^^^^^^^
AttributeError: 'ProjectOp' object has no attribute 'aliases'

```
