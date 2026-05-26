# FAILURE: Complex Let Bindings

**KQL:**
```kusto
let T1 = Table1 | extend factor = 100;
let T2 = Table2 | extend factor = 200;
T1 | union T2 | project factor, id
```

**Traceback:**
```python
Traceback (most recent call last):
  File "C:\Users\navka\navakanth001\kqlbridge\run_stress_test.py", line 163, in run
    _, pyspark_code = smart_transpile(kql.strip(), force_engine="pyspark")
                      ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
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
