-- ============================================================
-- KQLBridge STRESS + SECURITY TEST QUERY
-- Target: Parser limits, translation fidelity, injection
--         surface, window functions, recursion, type coercion,
--         NULL propagation, and subquery explosion
-- ============================================================

WITH

-- ── LAYER 1: Recursive CTE (tests recursion depth limit) ─────
recursive_depth AS (
    SELECT
        1                        AS depth,
        CAST('root' AS VARCHAR)  AS path,
        CAST(0 AS BIGINT)        AS accumulated_cost
    UNION ALL
    SELECT
        rd.depth + 1,
        CAST(rd.path + '/' + CAST(rd.depth AS VARCHAR) AS VARCHAR),
        rd.accumulated_cost + (rd.depth * rd.depth)
    FROM recursive_depth rd
    WHERE rd.depth < 64          -- stress the recursion cap
),

-- ── LAYER 2: Boundary & Type-Coercion Probe ──────────────────
boundary_probe AS (
    SELECT
        CAST(2147483647  AS INT)          AS int_max,
        CAST(-2147483648 AS INT)          AS int_min,
        CAST(9223372036854775807 AS BIGINT)  AS bigint_max,
        CAST(-9223372036854775808 AS BIGINT) AS bigint_min,
        CAST(1.7976931348623158E+308 AS FLOAT) AS float_max,
        CAST(2.2250738585072014E-308 AS FLOAT) AS float_min,
        CAST(NULL AS INT)                 AS null_int,
        CAST(NULL AS VARCHAR)             AS null_str,
        CAST('' AS VARCHAR)               AS empty_str,
        CAST('   ' AS VARCHAR)            AS whitespace_str,
        CAST('2099-12-31 23:59:59.999' AS DATETIME) AS far_future,
        CAST('1970-01-01 00:00:00.000' AS DATETIME) AS epoch,
        CAST('9999-12-31' AS DATE)        AS max_date,
        CAST('0001-01-01' AS DATE)        AS min_date,
        -- SQL injection surface probes embedded as data literals
        CAST(''' OR ''1''=''1'   AS VARCHAR) AS sqli_classic,
        CAST('"; DROP TABLE users;--'     AS VARCHAR) AS sqli_drop,
        CAST('1; EXEC xp_cmdshell(''id'')' AS VARCHAR) AS sqli_exec,
        CAST('${7*7}'                     AS VARCHAR) AS ssti_probe,
        CAST('{{7*7}}'                    AS VARCHAR) AS tplinjection,
        CAST('<script>alert(1)</script>'  AS VARCHAR) AS xss_probe,
        CAST(REPLICATE('A', 8000)         AS VARCHAR) AS long_string_8k,
        CAST(REPLICATE('A', 65535)        AS VARCHAR) AS long_string_64k
),

-- ── LAYER 3: Multi-join Fan-out Aggregation ───────────────────
event_metrics AS (
    SELECT
        e.source_ip,
        e.destination_ip,
        e.user_name,
        e.event_id,
        e.event_time,
        COUNT(*)                          OVER (PARTITION BY e.source_ip)             AS events_per_src,
        COUNT(*)                          OVER (PARTITION BY e.destination_ip)        AS events_per_dst,
        COUNT(DISTINCT e.user_name)       OVER (PARTITION BY e.source_ip
                                                ORDER BY e.event_time
                                                ROWS BETWEEN 999 PRECEDING AND CURRENT ROW)
                                                                                      AS distinct_users_window,
        SUM(e.bytes_sent)                 OVER (PARTITION BY e.source_ip
                                                ORDER BY e.event_time
                                                ROWS BETWEEN 59 PRECEDING AND CURRENT ROW)
                                                                                      AS rolling_60_bytes,
        AVG(CAST(e.response_time_ms AS FLOAT)) OVER (PARTITION BY e.destination_ip
                                                ORDER BY e.event_time
                                                RANGE BETWEEN INTERVAL '1' HOUR PRECEDING
                                                          AND CURRENT ROW)            AS avg_latency_1h,
        ROW_NUMBER()                      OVER (PARTITION BY e.source_ip, e.user_name
                                                ORDER BY e.event_time DESC)           AS rn_latest,
        RANK()                            OVER (ORDER BY e.bytes_sent DESC)           AS global_bytes_rank,
        DENSE_RANK()                      OVER (PARTITION BY e.source_ip
                                                ORDER BY e.severity DESC)             AS severity_dense_rank,
        NTILE(10)                         OVER (ORDER BY e.event_time)                AS decile,
        LAG(e.event_time, 1)              OVER (PARTITION BY e.source_ip
                                                ORDER BY e.event_time)                AS prev_event_time,
        LEAD(e.event_time, 1)             OVER (PARTITION BY e.source_ip
                                                ORDER BY e.event_time)                AS next_event_time,
        FIRST_VALUE(e.event_id)           OVER (PARTITION BY e.source_ip
                                                ORDER BY e.event_time
                                                ROWS BETWEEN UNBOUNDED PRECEDING
                                                         AND UNBOUNDED FOLLOWING)     AS first_event_in_session,
        LAST_VALUE(e.event_id)            OVER (PARTITION BY e.source_ip
                                                ORDER BY e.event_time
                                                ROWS BETWEEN UNBOUNDED PRECEDING
                                                         AND UNBOUNDED FOLLOWING)     AS last_event_in_session,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY e.bytes_sent)
                                          OVER (PARTITION BY e.destination_ip)        AS p95_bytes
    FROM SecurityEvents e
    WHERE
        e.event_time BETWEEN DATEADD(DAY, -90, GETUTCDATE()) AND GETUTCDATE()
        AND e.source_ip IS NOT NULL
        AND e.source_ip NOT IN ('0.0.0.0', '127.0.0.1', '::1')
        AND (
                e.severity >= 3
             OR e.bytes_sent > 1048576
             OR e.event_id IN (4624, 4625, 4648, 4672, 4688, 4698,
                                4720, 4732, 4756, 7045, 7036)
            )
),

-- ── LAYER 4: Threat Scoring — CASE-Heavy Logic ────────────────
threat_scored AS (
    SELECT
        em.*,
        DATEDIFF(SECOND, em.prev_event_time, em.event_time) AS inter_event_gap_sec,

        -- Composite threat score via nested CASE
        CASE
            WHEN em.events_per_src > 10000                        THEN 'CRITICAL'
            WHEN em.distinct_users_window > 50
                 AND em.rolling_60_bytes > 104857600              THEN 'HIGH'
            WHEN em.avg_latency_1h < 5
                 AND em.events_per_dst > 500                      THEN 'HIGH'
            WHEN em.global_bytes_rank <= 10                       THEN 'MEDIUM'
            ELSE                                                       'LOW'
        END AS threat_level,

        -- Behavioral anomaly score (0–100)
        LEAST(100,
            CASE WHEN em.events_per_src > 5000  THEN 30 ELSE 0 END
          + CASE WHEN em.rolling_60_bytes > 52428800 THEN 25 ELSE 0 END
          + CASE WHEN em.distinct_users_window > 20  THEN 20 ELSE 0 END
          + CASE WHEN em.avg_latency_1h < 10         THEN 15 ELSE 0 END
          + CASE WHEN em.severity_dense_rank = 1     THEN 10 ELSE 0 END
        ) AS anomaly_score,

        -- Time-gap anomaly
        CASE
            WHEN DATEDIFF(SECOND, em.prev_event_time, em.event_time) < 1   THEN 'BURST'
            WHEN DATEDIFF(SECOND, em.prev_event_time, em.event_time) < 10  THEN 'RAPID'
            WHEN DATEDIFF(SECOND, em.prev_event_time, em.event_time) < 60  THEN 'NORMAL'
            WHEN em.prev_event_time IS NULL                                 THEN 'FIRST'
            ELSE                                                               'SLOW'
        END AS event_velocity,

        -- String manipulation stress
        UPPER(TRIM(em.user_name))                                AS normalized_user,
        LOWER(SUBSTRING(em.source_ip, 1, CHARINDEX('.', em.source_ip) - 1)) AS src_octet1,
        LEN(em.user_name)                                        AS username_len,
        REVERSE(em.source_ip)                                    AS src_ip_reversed,
        REPLACE(REPLACE(em.user_name, '''', ''), ';', '')        AS sanitized_user,
        CONCAT(em.source_ip, ' → ', em.destination_ip, ' [', em.user_name, ']') AS flow_label,
        HASHBYTES('SHA2_256', CAST(em.event_id AS VARCHAR)
                            + em.source_ip
                            + em.user_name)                      AS event_fingerprint
    FROM event_metrics em
    WHERE em.rn_latest = 1   -- deduplicate to latest per (src, user)
),

-- ── LAYER 5: Lateral / Correlated Subquery Battery ───────────
enriched AS (
    SELECT
        ts.*,

        -- Correlated scalar subquery 1: user's first-ever event
        (SELECT MIN(e2.event_time)
         FROM SecurityEvents e2
         WHERE e2.user_name = ts.user_name) AS user_first_seen,

        -- Correlated scalar subquery 2: distinct destinations this source hit today
        (SELECT COUNT(DISTINCT e3.destination_ip)
         FROM SecurityEvents e3
         WHERE e3.source_ip = ts.source_ip
           AND e3.event_time >= CAST(GETUTCDATE() AS DATE)) AS dst_count_today,

        -- Correlated scalar subquery 3: max bytes in last 24h from this source
        (SELECT ISNULL(MAX(e4.bytes_sent), 0)
         FROM SecurityEvents e4
         WHERE e4.source_ip = ts.source_ip
           AND e4.event_time >= DATEADD(HOUR, -24, GETUTCDATE())) AS max_bytes_24h,

        -- EXISTS probe
        CASE WHEN EXISTS (
                SELECT 1
                FROM ThreatIntelligence ti
                WHERE ti.indicator = ts.source_ip
                  AND ti.confidence >= 70
                  AND ti.expiry_time > GETUTCDATE()
             ) THEN 1 ELSE 0 END                                 AS is_known_threat,

        -- NOT EXISTS probe
        CASE WHEN NOT EXISTS (
                SELECT 1
                FROM Allowlist al
                WHERE al.ip_address = ts.source_ip
                  AND al.active = 1
             ) THEN 1 ELSE 0 END                                 AS not_allowlisted,

        -- IN with large subquery list
        CASE WHEN ts.event_id IN (
                SELECT DISTINCT event_id
                FROM CriticalEventCatalog
                WHERE category IN ('PrivilegeEscalation',
                                   'LateralMovement',
                                   'CredentialAccess',
                                   'Exfiltration',
                                   'Persistence')
                  AND criticality = 'HIGH'
             ) THEN 1 ELSE 0 END                                 AS is_critical_event
    FROM threat_scored ts
),

-- ── LAYER 6: Set Operations — UNION / INTERSECT / EXCEPT ──────
combined_alerts AS (
    -- High severity from primary telemetry
    SELECT source_ip, user_name, event_time, 'PRIMARY'  AS alert_source, anomaly_score
    FROM enriched
    WHERE threat_level IN ('CRITICAL', 'HIGH')
      AND is_known_threat = 1

    UNION ALL

    -- Same IPs from a secondary honeypot log
    SELECT h.attacker_ip, h.lure_user, h.hit_time, 'HONEYPOT', 95
    FROM HoneypotHits h
    WHERE h.hit_time >= DATEADD(DAY, -30, GETUTCDATE())

    UNION ALL

    -- Recursive depth boundary hits (stress layer re-join)
    SELECT
        '0.0.0.0',
        'recursive_probe_' + CAST(rd.depth AS VARCHAR),
        GETUTCDATE(),
        'RECURSION_STRESS',
        rd.depth
    FROM recursive_depth rd
    WHERE rd.depth = 64     -- only boundary row

    INTERSECT

    -- Filter to only those also appearing in EDR telemetry
    SELECT e.source_ip, e.user_name, e.event_time, e.alert_source, e.anomaly_score
    FROM (
        SELECT source_ip, user_name, event_time, 'PRIMARY' AS alert_source, anomaly_score
        FROM enriched
        WHERE is_critical_event = 1
    ) e
    INNER JOIN EDRAlerts edr
        ON edr.host_ip = e.source_ip
       AND edr.user_name = e.user_name
       AND ABS(DATEDIFF(SECOND, edr.alert_time, e.event_time)) < 300

    EXCEPT

    -- Remove already-suppressed alerts
    SELECT s.ip, s.user_name, s.suppression_start, s.reason, 0
    FROM AlertSuppressions s
    WHERE s.suppression_end > GETUTCDATE()
      AND s.auto_suppressed = 0
),

-- ── LAYER 7: Final Pivot + JSON / XML Stress ─────────────────
pivoted_severity AS (
    SELECT
        source_ip,
        SUM(CASE WHEN threat_level = 'CRITICAL' THEN 1 ELSE 0 END) AS cnt_critical,
        SUM(CASE WHEN threat_level = 'HIGH'     THEN 1 ELSE 0 END) AS cnt_high,
        SUM(CASE WHEN threat_level = 'MEDIUM'   THEN 1 ELSE 0 END) AS cnt_medium,
        SUM(CASE WHEN threat_level = 'LOW'      THEN 1 ELSE 0 END) AS cnt_low,
        MAX(anomaly_score)                                           AS peak_score,
        MIN(event_time)                                              AS earliest,
        MAX(event_time)                                              AS latest,
        DATEDIFF(MINUTE,
                 MIN(event_time),
                 MAX(event_time))                                    AS campaign_duration_min,
        STRING_AGG(DISTINCT event_velocity, ', ')
            WITHIN GROUP (ORDER BY event_velocity)                   AS velocity_modes
    FROM enriched
    GROUP BY source_ip
    HAVING
        COUNT(*) > 5
        AND (
               MAX(anomaly_score) >= 50
            OR SUM(CASE WHEN threat_level = 'CRITICAL' THEN 1 ELSE 0 END) > 0
           )
)

-- ══════════════════════════════════════════════════════════════
-- FINAL SELECT — All layers assembled
-- ══════════════════════════════════════════════════════════════
SELECT
    -- Identity
    e.source_ip,
    e.destination_ip,
    e.normalized_user                                            AS user_name,
    e.event_id,
    e.event_time,

    -- Scoring & classification
    e.threat_level,
    e.anomaly_score,
    e.event_velocity,
    e.is_known_threat,
    e.not_allowlisted,
    e.is_critical_event,

    -- Pivot summary
    p.cnt_critical,
    p.cnt_high,
    p.cnt_medium,
    p.cnt_low,
    p.peak_score,
    p.campaign_duration_min,
    p.velocity_modes,

    -- Window stats
    e.events_per_src,
    e.rolling_60_bytes,
    e.avg_latency_1h,
    e.p95_bytes,
    e.distinct_users_window,
    e.global_bytes_rank,
    e.decile,

    -- Derived fields
    e.flow_label,
    e.event_fingerprint,
    e.inter_event_gap_sec,
    e.user_first_seen,
    e.dst_count_today,
    e.max_bytes_24h,

    -- Alert correlation
    ca.alert_source,

    -- Boundary probes (single-row cross-join to stress type system)
    bp.int_max,
    bp.bigint_min,
    bp.float_max,
    bp.null_int,
    bp.null_str,
    bp.empty_str,
    bp.far_future,
    bp.epoch,

    -- Security literal probes (test KQL escaping fidelity)
    bp.sqli_classic,
    bp.sqli_drop,
    bp.sqli_exec,
    bp.ssti_probe,
    bp.xss_probe,
    LEN(bp.long_string_8k)                                       AS long_str_8k_len,
    LEN(bp.long_string_64k)                                      AS long_str_64k_len,

    -- Recursive depth max (stress the CTE unroll)
    (SELECT MAX(depth) FROM recursive_depth)                     AS recursion_max_depth,
    (SELECT MAX(accumulated_cost) FROM recursive_depth)          AS recursion_peak_cost,

    -- Timestamp math
    GETUTCDATE()                                                 AS query_exec_utc,
    DATEADD(HOUR, 5, GETUTCDATE())                               AS ist_approx,
    DATEDIFF(DAY, e.user_first_seen, GETUTCDATE())               AS user_age_days,

    -- NULL-coalescing chain
    COALESCE(e.normalized_user, e.user_name, 'UNKNOWN')          AS user_display,
    ISNULL(e.inter_event_gap_sec, -1)                            AS gap_or_neg1,
    NULLIF(e.anomaly_score, 0)                                   AS score_nullif_zero,

    -- Deeply nested scalar expression
    CASE
        WHEN (
            CASE
                WHEN e.is_known_threat = 1 AND e.anomaly_score > 75
                THEN 'CONFIRMED'
                WHEN e.is_known_threat = 1 AND e.anomaly_score BETWEEN 50 AND 75
                THEN 'PROBABLE'
                ELSE 'SUSPECTED'
            END
        ) = 'CONFIRMED'
        AND e.not_allowlisted = 1
        AND e.dst_count_today > 10
        THEN 'INVESTIGATE_NOW'
        WHEN p.cnt_critical > 3
        THEN 'ESCALATE'
        ELSE 'MONITOR'
    END                                                          AS final_disposition

FROM enriched e

-- Pivot join (LEFT to keep all enriched rows even without aggregation)
LEFT JOIN pivoted_severity p
    ON p.source_ip = e.source_ip

-- Alert correlation (LEFT; row may not appear in combined_alerts)
LEFT JOIN combined_alerts ca
    ON ca.source_ip  = e.source_ip
   AND ca.user_name  = e.normalized_user

-- Cross-join single-row boundary probe (deliberate fan-out: 1 row × N)
CROSS JOIN (SELECT TOP 1 * FROM boundary_probe) bp

WHERE
    -- Must pass at least one threat gate
    (
        e.threat_level IN ('CRITICAL', 'HIGH')
        OR e.anomaly_score >= 60
        OR (e.is_known_threat = 1 AND e.is_critical_event = 1)
    )
    -- Exclude recursive stress artifact rows
    AND e.source_ip <> '0.0.0.0'

    -- Deep predicate nesting
    AND (
            (e.events_per_src > 1000  AND e.rolling_60_bytes > 10485760)
         OR (e.avg_latency_1h < 20    AND e.distinct_users_window > 5)
         OR (e.global_bytes_rank <= 100
             AND e.decile >= 9
             AND e.event_velocity IN ('BURST', 'RAPID'))
         OR (
                e.not_allowlisted = 1
                AND e.is_known_threat = 1
                AND e.dst_count_today >
                    (SELECT AVG(CAST(sub.dst_count_today AS FLOAT))
                     FROM enriched sub
                     WHERE sub.threat_level = 'HIGH') * 1.5
            )
        )

ORDER BY
    e.anomaly_score           DESC,
    e.threat_level            ASC,
    p.campaign_duration_min   DESC NULLS LAST,
    e.event_time              DESC

OPTION (
    MAXRECURSION 64,
    RECOMPILE,
    HASH JOIN,
    MERGE JOIN,
    LOOP JOIN,
    FORCE ORDER,
    MAXDOP 8,
    FAST 100
);
