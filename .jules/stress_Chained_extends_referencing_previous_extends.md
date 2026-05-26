# FAILURE: Chained extends referencing previous extends

**KQL:**
```kusto
SecurityEvents
| extend base_score = 50
| extend final_score = base_score + 10
| project final_score
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
