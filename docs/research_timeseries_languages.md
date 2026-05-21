# Research: Time-Series Languages & Databases for KQL Micro Model

## Executive Summary

The KQL `make-series` operator is conceptually aligned with **7 distinct paradigms** across
production time-series systems. Understanding each reveals the best translation strategies.

---

## 1. TSQL2 / SQL:2011 Temporal Tables (ISO Standard)

### The Standard
SQL:2011 added temporal table support with two table types:
- **System-Time Temporal**: tracks transaction history (`SYSTEM VERSIONING`)
- **Application-Time Temporal** (valid-time): tracks real-world valid periods

### Allen's Interval Operators in SQL:2011
SQL:2011 introduced `PERIOD` predicates for interval algebra:
```sql
-- Overlap: A overlaps B
WHERE PERIOD(t1.valid_from, t1.valid_to) OVERLAPS PERIOD(t2.valid_from, t2.valid_to)

-- Contains: A contains point P  
WHERE PERIOD(t1.valid_from, t1.valid_to) CONTAINS p.event_time

-- Immediately Precedes
WHERE PERIOD(t1.valid_from, t1.valid_to) IMMEDIATELY PRECEDES PERIOD(t2.valid_from, t2.valid_to)
```

### Snodgrass Coalescing (PACK / COALESCE)
Richard Snodgrass' temporal database book defines:
- **COALESCE**: Merges adjacent/overlapping intervals with same key+value into maximal intervals
- **PACK**: Groups and coalesces a relation
- **UNPACK**: Expands intervals into a timeline of points

#### SQL Island-Grouping Pattern for COALESCE:
```sql
-- Step 1: Mark interval starts (where previous row's end != current row's start)
WITH gaps AS (
    SELECT *,
        CASE WHEN LAG(valid_to) OVER (PARTITION BY entity_key ORDER BY valid_from)
                  = valid_from THEN 0 ELSE 1 END AS is_new_island
    FROM intervals
),
-- Step 2: Create island ID via cumsum
islands AS (
    SELECT *, SUM(is_new_island) OVER (PARTITION BY entity_key ORDER BY valid_from) AS island_id
    FROM gaps
),
-- Step 3: Collapse each island to its min/max boundary  
coalesced AS (
    SELECT entity_key, MIN(valid_from) AS valid_from, MAX(valid_to) AS valid_to
    FROM islands
    GROUP BY entity_key, island_id
)
```

### KQL Translation
KQL's `series_coalesce()` maps directly to the island-grouping pattern above.

---

## 2. TimescaleDB: time_bucket_gapfill()

### Architecture
TimescaleDB implements gap-filling as a **custom PostgreSQL scan node** that intercepts
the query planner. It does NOT work as a pure UDF — it modifies the execution plan.

### Syntax
```sql
SELECT 
    time_bucket_gapfill('1 hour', time) AS bucket,
    device_id,
    locf(avg(temperature)) AS temp_filled,     -- Last Observation Carried Forward
    interpolate(avg(humidity)) AS hum_interp   -- Linear interpolation
FROM measurements
WHERE time BETWEEN '2024-01-01' AND '2024-01-02'
GROUP BY bucket, device_id;
```

### Architecture Notes
- `time_bucket_gapfill` must be a **top-level GROUP BY expression** (not nested)
- `locf()` and `interpolate()` are **marker functions** that signal the scan node — not standalone UDFs
- The scan node tracks "previous known value" and "next known value" for interpolation
- Without this scan node, the functions would throw errors

### Translation to Standard SQL
TimescaleDB's semantics translate to our CTE + window function pattern:
```sql
-- TimescaleDB:  interpolate(avg(temperature))
-- Standard SQL: linear interpolation via window lag/lead
LAST_VALUE(avg_val) IGNORE NULLS OVER (PARTITION BY device ORDER BY bucket ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)
+ (bucket_as_float - last_known_time_float)
/ (next_known_time_float - last_known_time_float)
* (next_val - last_val)
```

### Key Insight for KQL Micro Model
TimescaleDB's architecture confirms that **gap-filling requires a two-pass approach**:
1. Generate contiguous time grid (PostgreSQL recursive CTE or `generate_series`)
2. Join sparse data onto grid, then apply marker-based interpolation

Our TEG v5 implements this correctly via `complete_grid` CTE + window interpolation.

---

## 3. DuckDB Time-Series Features

### time_bucket() Function
```sql
-- DuckDB native time bucketing
SELECT 
    time_bucket(INTERVAL '1 hour', timestamp) AS bucket,
    AVG(temperature) AS avg_temp
FROM measurements
GROUP BY 1, device_id;
```

### Native ASOF JOIN (DuckDB's killer feature)
DuckDB has the most elegant ASOF join syntax in any SQL engine:
```sql
SELECT t.*, p.price
FROM trades t
ASOF JOIN prices p 
  ON t.symbol = p.symbol 
  AND t.when >= p.when;
-- DuckDB optimizes this internally using sort + merge, NOT nested loops
```

**Left ASOF** (keeps unmatched left rows as NULL):
```sql
SELECT *
FROM trades t
ASOF LEFT JOIN prices p USING (symbol, when);
```

### Gap-Fill via generate_series
```sql
-- DuckDB gap-fill via generate_series + lateral join
SELECT 
    g.ts AS bucket,
    device_id,
    COALESCE(AVG(temperature), 0) AS temp_filled
FROM generate_series(
    TIMESTAMPTZ '2024-01-01', 
    TIMESTAMPTZ '2024-01-02', 
    INTERVAL '1 hour'
) AS g(ts)
CROSS JOIN (SELECT DISTINCT device_id FROM measurements) d
LEFT JOIN measurements m 
    ON m.device_id = d.device_id
    AND time_bucket(INTERVAL '1 hour', m.timestamp) = g.ts
GROUP BY g.ts, device_id
ORDER BY device_id, bucket;
```

### KQL Micro Model Opportunity
DuckDB should be a **new 5th target dialect** for our emitter registry:
- Cleaner ASOF JOIN (no row-number fallback needed)
- `time_bucket()` instead of `date_trunc()` 
- `generate_series()` instead of recursive CTE

---

## 4. InfluxDB Flux Language

### Pipe-Forward Operator Model
Flux uses `|>` (pipe-forward) exactly like KQL uses `|` (pipe). Both are **pipeline-oriented DSLs**.

```flux
// Flux: time-series aggregation with gap fill
from(bucket: "telemetry")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "cpu")
  |> aggregateWindow(every: 1h, fn: mean, createEmpty: true)
  |> fill(usePrevious: true)
```

### KQL Parallel
```kql
// KQL equivalent
Metrics
| where TimeGenerated > ago(7d) and Measurement == "cpu"  
| make-series avg(Value) on TimeGenerated from ago(7d) to now() step 1h by Device
| series_fill_forward()
```

### Semantic Differences: Flux vs KQL
| Concept | Flux | KQL make-series |
|---------|------|-----------------|
| Time window | `aggregateWindow(every: 1h)` | `step 1h` |
| Gap fill constant | `fill(value: 0.0)` | `default = 0` |
| Gap fill forward | `fill(usePrevious: true)` | `series_fill_forward()` |
| Linear interpolation | Not native (requires join trick) | `series_fill_linear()` |
| Group by | `group(columns: ["device"])` | `by Device` |
| Output format | Stream of tables | Array of values per group |

### Key Design Insight
Flux's architecture shows that **pipeline operators compose sequentially** on a stream of tables.
KQL's `make-series` is a **fold operation** that collapses a table into grouped arrays.
Our TEG IR should represent both models — point-by-point (Flux/Spark/T-SQL) and array-based (KQL native).

---

## 5. PromQL / MetricsQL

### Range Vectors & Instant Vectors
```promql
# Instant vector: value at a single moment
http_requests_total{job="api"}

# Range vector: values over a time window
http_requests_total{job="api"}[5m]  # last 5 minutes of samples

# Aggregation over time
rate(http_requests_total{job="api"}[5m])     # per-second rate over 5m window
increase(http_requests_total{job="api"}[1h]) # total increase over 1h
```

### Key Semantic Differences from SQL
- PromQL has **no concept of tables** — all data is metric-based (name + labels + value + timestamp)
- **Rate vs Sum**: PromQL `rate()` is fundamentally different from SQL `SUM()/TIMESTAMPDIFF()`
- **Instant query**: Returns values at NOW; **Range query**: Returns a matrix over time
- **No joins**: PromQL has binary operators (`and`, `or`, `unless`) but NOT SQL-style joins

### MetricsQL Extensions (VictoriaMetrics)
MetricsQL adds functions not in PromQL:
```promql
# Linear interpolation (MetricsQL extension)
interpolate(metric_name[1h])

# Moving average (MetricsQL)
rollup_candlestick(metric[1h])  # OHLC candle

# Outlier detection
outlier_iqr(metric[1h], 1.5)   # IQR-based outlier removal
```

### KQL Translation Opportunity
KQL `series_stats()` is conceptually similar to MetricsQL's `rollup_candlestick()`.
Our TEG v5 `TEGWindowSpec` should support OHLC-style multiple output columns.

---

## 6. Flink SQL: Streaming Time Windows

### Window TVF Syntax (Flink 1.13+)
```sql
-- Tumbling window (non-overlapping fixed size)
SELECT window_start, window_end, device_id, AVG(temp) AS avg_temp
FROM TABLE(TUMBLE(TABLE sensor_data, DESCRIPTOR(event_time), INTERVAL '1' HOUR))
GROUP BY window_start, window_end, device_id;

-- Sliding/Hop window (overlapping, slide < size)
SELECT window_start, window_end, device_id, AVG(temp)
FROM TABLE(HOP(TABLE sensor_data, DESCRIPTOR(event_time), INTERVAL '5' MINUTE, INTERVAL '1' HOUR))
GROUP BY window_start, window_end, device_id;

-- Session window (activity-based gaps)
SELECT window_start, window_end, user_id, COUNT(*) AS clicks
FROM TABLE(SESSION(TABLE clickstream, DESCRIPTOR(event_time), INTERVAL '30' MINUTE))
GROUP BY window_start, window_end, user_id;
```

### Temporal Join (Event time + Versioned table)
```sql
-- Enrich orders with price at the time of the order
SELECT o.order_id, p.price, o.quantity, p.price * o.quantity AS total
FROM orders o
LEFT JOIN product_prices FOR SYSTEM_TIME AS OF o.order_time AS p
  ON o.product_id = p.product_id;
```

### Gap-Filling in Flink SQL
Flink SQL does NOT have native gap-filling. The pattern is:
```sql
-- Generate time spine as a source
WITH spine AS (
    SELECT * FROM TABLE(
        GENERATE_SERIES(TIMESTAMP '2024-01-01', TIMESTAMP '2024-01-02', INTERVAL '1' HOUR)
    )
),
-- Left join with actual data
filled AS (
    SELECT s.ts, d.device_id, COALESCE(m.value, 0) AS value
    FROM spine s
    CROSS JOIN (SELECT DISTINCT device_id FROM measurements) d
    LEFT JOIN measurements m ON m.device_id = d.device_id AND m.bucket = s.ts
)
```

### KQL Translation Insight
Flink's HOP window (sliding) maps to KQL's `series_fir()` (Finite Impulse Response filter),
which implements a moving average. Our `TEGWindowSpec` should emit Flink's HOP TVF syntax
when targeting a streaming SQL dialect.

---

## 7. Snodgrass Temporal DB: COALESCE, PACK, UNPACK Operators

### COALESCE
Merges tuples with same non-temporal attributes whose temporal intervals are adjacent or overlapping.

```sql
-- Snodgrass SQL/Temporal COALESCE rewrite pattern
-- Input: Salary changes for employees
-- employee_id | salary | valid_from | valid_to
-- 1           | 50000  | 2020-01-01 | 2021-01-01
-- 1           | 50000  | 2021-01-01 | 2022-01-01   ← same salary, adjacent intervals

-- After COALESCE:
-- 1           | 50000  | 2020-01-01 | 2022-01-01   ← merged into one interval

-- Implementation (island grouping):
WITH consecutive AS (
    SELECT *,
        CASE WHEN LAG(valid_to) OVER (PARTITION BY employee_id, salary ORDER BY valid_from)
                   = valid_from THEN 0 ELSE 1 END AS new_island
    FROM salary_history
),
grouped AS (
    SELECT *, SUM(new_island) OVER (PARTITION BY employee_id, salary ORDER BY valid_from) AS island
    FROM consecutive
)
SELECT employee_id, salary, MIN(valid_from) AS valid_from, MAX(valid_to) AS valid_to
FROM grouped
GROUP BY employee_id, salary, island;
```

### PACK (Temporal Projection)
Removes non-temporal redundancy, then COALESCEs. Useful after projecting away columns.

### UNPACK (Discretization)
Expands each interval into one row per time unit. The inverse of COALESCE.
**This is fundamentally what `make-series` does** — it discretizes the event timeline
into a dense grid of time buckets.

### Connection to KQL
- KQL `make-series` = **UNPACK** (discretize events into time buckets with gap-filling)
- KQL `series_coalesce()` = **COALESCE** (merge adjacent identical array segments)
- Our `TEGCoalesceSpec` in TEG v5 implements the island-grouping COALESCE pattern

---

## Summary: Translation Matrix

| KQL Construct | TimescaleDB | DuckDB | Flux | Flink SQL | Snodgrass |
|---------------|-------------|--------|------|-----------|-----------|
| `make-series ... step 1h` | `time_bucket_gapfill('1h', ...)` | `time_bucket(INTERVAL '1h', ...)` + `generate_series` | `aggregateWindow(every: 1h)` | `TUMBLE(..., INTERVAL '1' HOUR)` | UNPACK |
| `series_fill_forward()` | `locf(...)` | `LAST_VALUE IGNORE NULLS OVER(...)` | `fill(usePrevious: true)` | N/A (custom) | N/A |
| `series_fill_linear()` | `interpolate(...)` | Window lag/lead computation | N/A (requires join) | N/A (custom) | N/A |
| `series_coalesce()` | N/A | Island grouping pattern | N/A | N/A | COALESCE |
| `series_fir()` (moving avg) | `avg() OVER (ROWS n PRECEDING)` | Same | `movingAverage(n)` | HOP window | N/A |
| `series_join_asof()` | N/A | `ASOF JOIN` | N/A | Temporal Join | N/A |
| `series_join_overlap()` | N/A | `OVERLAPS` predicate | N/A | Interval join | Allen's operators |
