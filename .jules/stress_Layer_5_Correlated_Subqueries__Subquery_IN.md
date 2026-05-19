# FAILURE: Layer 5: Correlated Subqueries / Subquery IN

**KQL:**
```kusto
SecurityEvents
| where source_ip in ("1.2.3.4", "5.6.7.8")
```

**Traceback:**
```python
Traceback (most recent call last):
  File "C:\Users\navka\navakanth001\kqlbridge\run_stress_test.py", line 131, in run
    _, pyspark_code = smart_transpile(kql.strip(), force_engine="pyspark")
                      ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\navka\navakanth001\kqlbridge\src\kqlbridge\smart.py", line 38, in smart_transpile
    return "pyspark", gen.generate(query)
                      ~~~~~~~~~~~~^^^^^^^
  File "C:\Users\navka\navakanth001\kqlbridge\src\kqlbridge\generators\pyspark.py", line 18, in generate
    lines.append(f"df = spark.table('{query.table.table_name}')")
                                      ^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'str' object has no attribute 'table_name'

```
