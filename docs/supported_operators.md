# Supported KQL Operators — KQLBridge v0.1

This document defines the explicit translation scope for KQLBridge v0.1.
Every operator listed here has a corresponding eval case in `tests/eval/benchmark.json`.

---

## v0.1 Scope — 14 Operators

### 01 · `where` → `WHERE clause`

```kql
AppLogs | where Level == 'Error' and Duration > 500
→ SELECT * FROM AppLogs WHERE Level = 'Error' AND Duration > 500
```

Supported predicates: `==`, `!=`, `<`, `<=`, `>`, `>=`, `and`, `or`, `not`,
`contains`, `startswith`, `endswith`, `has`, `in`, `!in`, `isnotnull`, `isnull`.

---

### 02 · `project` → `SELECT columns`

```kql
AppLogs | project Message, Level, ServiceName
→ SELECT Message, Level, ServiceName FROM AppLogs
```

---

### 03 + 04 · `summarize` → `GROUP BY + aggregations`

```kql
AppLogs | summarize count() by ServiceName
→ SELECT ServiceName, COUNT(*) FROM AppLogs GROUP BY ServiceName
```

Supported aggregation functions: `count()`, `sum()`, `avg()`, `min()`, `max()`, `dcount()`, `countif()`.

> ⚠ **Human review required.** The summarize → GROUP BY rewrite is the highest-risk
> semantic translation. See `context/operator_summarize.skill` for edge cases.

---

### 05 · `bin()` → `DATE_TRUNC / FLOOR`

```kql
| summarize count() by bin(TimeGenerated, 1h)
→ GROUP BY DATE_TRUNC('hour', TimeGenerated)
```

Sub-minute bins (e.g. `5m`) use `FLOOR(UNIX_TIMESTAMP(...)/300)*300` logic.

---

### 06 · `ago()` → `CURRENT_TIMESTAMP - INTERVAL`

```kql
| where TimeGenerated > ago(24h)
→ WHERE TimeGenerated > CURRENT_TIMESTAMP - INTERVAL '24 hours'
```

---

### 07 · `extend` → `SELECT *, computed_col AS expr`

```kql
AppLogs | extend MsgUpper = toupper(Message)
→ SELECT *, UPPER(Message) AS MsgUpper FROM AppLogs
```

---

### 08 · `order by` / `sort by` → `ORDER BY`

```kql
AppLogs | order by TimeGenerated desc
→ SELECT * FROM AppLogs ORDER BY TimeGenerated DESC
```

Both `order by` and `sort by` are accepted.

---

### 09 · `take` / `limit` → `LIMIT n`

```kql
AppLogs | take 100  →  SELECT * FROM AppLogs LIMIT 100
AppLogs | limit 50  →  SELECT * FROM AppLogs LIMIT 50
```

---

### 10 · `distinct` → `SELECT DISTINCT`

```kql
AppLogs | distinct Level, ServiceName
→ SELECT DISTINCT Level, ServiceName FROM AppLogs
```

---

### 11 · `join` (inner) → `INNER JOIN`

```kql
AppLogs | join (Users) on UserId
→ SELECT * FROM AppLogs INNER JOIN Users ON AppLogs.UserId = Users.UserId
```

Supported kinds: `inner`, `leftouter`, `rightouter`, `fullouter`.

---

### 12 · `union` → `UNION ALL`

```kql
AppLogs | union ErrorLogs
→ SELECT * FROM AppLogs UNION ALL SELECT * FROM ErrorLogs
```

---

### 13 · `let` variables → CTEs (`WITH ... AS`)

```kql
let errors = AppLogs | where Level == 'Error';
errors | summarize count() by ServiceName
```
```sql
WITH errors AS (SELECT * FROM AppLogs WHERE Level = 'Error')
SELECT ServiceName, COUNT(*) FROM errors GROUP BY ServiceName
```

---

### 14 · `count()` → `COUNT(*)`

```kql
AppLogs | count
→ SELECT COUNT(*) AS count_ FROM AppLogs
```

---

## String Function Support (via `extend`)

| KQL | Spark SQL |
|---|---|
| `tostring(x)` | `CAST(x AS STRING)` |
| `toint(x)` | `CAST(x AS INT)` |
| `tolower(x)` | `LOWER(x)` |
| `toupper(x)` | `UPPER(x)` |
| `strlen(x)` | `LENGTH(x)` |
| `substring(x, s, n)` | `SUBSTRING(x, s, n)` |
| `strcat(a, b)` | `a \|\| b` |
| `trim(x)` | `TRIM(x)` |
| `replace(x, a, b)` | `REPLACE(x, a, b)` |
| `now()` | `CURRENT_TIMESTAMP` |
| `startofday(t)` | `DATE_TRUNC('day', t)` |
| `startofhour(t)` | `DATE_TRUNC('hour', t)` |
| `startofmonth(t)` | `DATE_TRUNC('month', t)` |
| `dayofweek(t)` | `DAYOFWEEK(t)` |
| `hourofday(t)` | `HOUR(t)` |
