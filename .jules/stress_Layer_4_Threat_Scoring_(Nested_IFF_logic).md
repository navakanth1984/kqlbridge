# FAILURE: Layer 4: Threat Scoring (Nested IFF logic)

**KQL:**
```kusto
SecurityEvents
| extend threat_level = iff(events_per_src > 10000, "CRITICAL", iff(events_per_src <= 10, "MEDIUM", "LOW"))
| project threat_level
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
