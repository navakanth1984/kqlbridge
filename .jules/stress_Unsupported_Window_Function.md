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
  File "/app/run_stress_test.py", line 157, in run
    engine, code = smart_transpile(kql.strip())
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/src/kqlbridge/smart.py", line 110, in smart_transpile
    return "spark_sql", gen.generate(optimized_query)
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/src/kqlbridge/generators/spark_sql.py", line 55, in generate
    return self._build_body(query)
           ^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/src/kqlbridge/generators/spark_sql.py", line 181, in _build_body
    raise NotImplementedError("The serialize operator is not supported. Use 'order by' instead to establish window partitions.")
NotImplementedError: The serialize operator is not supported. Use 'order by' instead to establish window partitions.

```
