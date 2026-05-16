# Unsupported KQL Operators — KQLBridge v0.1

These operators have **no meaningful SQL equivalent** and will never be translated by KQLBridge.
Queries using them should be routed to the native KQL engine (Eventhouse / ADX).

We document them explicitly rather than hiding them. This is the Karpathy Principle 1 applied
to product design: state the scope before writing a line of code.

---

## Permanently Out of Scope

These will not be added in any KQLBridge version:

### `make-series`
Generates a time-series array column — a fundamentally different data model than SQL rows.
No SQL equivalent without losing the semantic meaning.

```kql
// No SQL equivalent — keep in KQL engine
AppLogs | make-series count() on TimeGenerated step 1h
```

### `series_decompose_anomalies()`
ML-based anomaly detection operator. Requires time-series data as input.
No SQL equivalent without a complete ML framework.

### `bag_unpack()`
Dynamically expands a JSON property bag into columns at query time.
This breaks the typed column model that SQL databases require.

### `render`
A visualization instruction — tells the Kusto UI how to display results.
SQL has no visualization layer at the query level.

### `ipv4_is_in_range()` / `ipv4_compare()`
Network-specific operators with no standard SQL mapping.
Available in some databases as extensions — not in standard Spark SQL.

### User-Defined Functions (ADX-registered UDFs)
Functions registered on an ADX cluster are cluster-specific and unknowable
at transpile time. KQLBridge cannot translate what it cannot see.

---

## Deferred to v0.2

These operators have SQL equivalents but are not in scope for v0.1:

| Operator | Planned SQL output | ETA |
|---|---|---|
| `parse` operator | `REGEXP_EXTRACT` (partial) | v0.2 |
| `mv-expand` | `EXPLODE / LATERAL VIEW` | v0.2 |
| `join kind=leftouter` | `LEFT OUTER JOIN` | v0.2 ✅ already implemented |
| `lookup` | `LEFT JOIN enrichment` | v0.2 |
| `evaluate` (basic) | plugin-style subquery | v0.2 |
| `strcat()` | `CONCAT(a, b)` | v0.1 ✅ already in string functions |
| `tostring()` / `toint()` | `CAST(x AS STRING/INT)` | v0.1 ✅ already in string functions |

---

## How to Handle Unsupported Operators

```python
from kqlbridge import is_supported, check

query = "AppLogs | make-series count() on TimeGenerated step 1h"

if not is_supported(query):
    # Route to Eventhouse / ADX — keep the query in KQL
    result = kql_client.execute(query)
else:
    sql = translate(query, target="spark")
    result = spark.sql(sql)
```

The `check()` function returns detailed error messages explaining which
operators are unsupported and why.
