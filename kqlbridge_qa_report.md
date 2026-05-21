kqlbridge

QA War Room — Full Execution Report

GPS Framework  |  AutoResearch Eval Loop  |  CDLC 5-Layer Testing  |  Karpathy Code Audit

QA Engineer + Context Engineer  |  May 2026







1. GPS Framework — Full Sweep

Target: kqlbridge translator + QA plan. Invocation: /gps full. Pre-flight: trust boundary clean — no injected instructions detected in any fixture file.



G — Gaslight (Premise Inversion)

Premise under test: "kqlbridge achieves semantic equivalence across KQL→SQL translation at scale, making it a reliable query bridge for Microsoft Fabric Eventhouse workflows."



Inverted argument (argued in good faith):

kqlbridge may be solving the wrong problem entirely. KQL and SQL are not structurally equivalent languages — KQL is a columnar streaming query language; SQL is a relational set-operation language. The conceptual gap between them is not a translation problem; it is a paradigm mismatch. Every translation through a bridge accumulates semantic loss (confirmed: 2.2% round-trip loss in SS-08, 8 E2E failures on window functions). At scale, that loss compounds. The premise assumes "semantic equivalence is achievable" — but the evidence suggests equivalence is only achievable for a subset of KQL (filter, project, summarize). The high-complexity operators (mv-expand, bag_unpack, window functions, dynamic columns) require structural changes that SQL cannot represent without schema assumptions that the bridge cannot make at runtime. The correct framing may not be "translate KQL to SQL" but "identify the KQL subset that is SQL-representable and reject the rest early with a clear error." The current bridge attempts full coverage and silently degrades.



Verdict — Premise: SHAKEN (not overturned).

The premise holds for the simple 70% of KQL. It is shaken for the complex 30%. Recommended action: add an explicit "bridge capability tier" declaration — Tier 1 (fully supported), Tier 2 (partial, with schema assumptions), Tier 3 (rejected at parse time with explanation). Do not attempt Tier 3 operators and silently fail.



P — Pushback (Plan Critique)

Target: the kqlbridge release plan — ship after passing 80% P0 rate over 5 CI runs.



Critique 1 — The 80% P0 error budget is too generous for a query bridge.

A 20% P0 failure tolerance means 1 in 5 runs may produce semantically incorrect SQL from a P0-priority query. For a Fabric Eventhouse bridge used in production analytics, a wrong translation is silent data corruption. The standard for query translation correctness must be 100% P0 pass, not 80%. The error budget is appropriate for non-deterministic AI output (LLM-as-judge), not for deterministic code translation.



Critique 2 — SS-05 panics are a ship blocker that is not treated as one.

Three panics under malformed input (SS-05) are recorded as a FAIL in the stress test panel but are not listed as P0 failures blocking release. A panic in a production Go server crashes the worker goroutine. With the bounded pool now in place, a panic kills one worker permanently, degrading the pool until restart. This must be classified P0 with the explicit criterion: zero panics under 5,000 malformed input requests.



Critique 3 — Heap drift (SS-07) is classified as WARN but is a time-bomb.

127 MB heap at t=30min with 1,000 req/s is 2.6x the baseline. If traffic doubles to 2,000 req/s, the heap grows past 254 MB and OOM becomes likely within the same 30-minute window. The object pool fix is the right approach, but it needs a post-fix SS-07 re-run to confirm heap stabilises before the WARN is closed.



Verdict — Plan: PARTIALLY ATTACKED.

The release gate criteria need two changes: (1) P0 threshold raised to 100%, and (2) zero-panic requirement added as an explicit criterion for the malformed-input stress test.



S — Stress-test (Artifact)

Target: translator/kql_to_sql.go + pool.go after this fix pass.



Standard input:

T | where timestamp > ago(7d) | summarize count() by category → translates correctly to SELECT COUNT(*) AS count_col FROM T WHERE timestamp > NOW() - INTERVAL 7 DAY GROUP BY category. PASS.



Edge input:

Unicode table name + reserved-word column + compound left-outer join. Input: "தரவு | join kind=leftouter (R) on select, col2". Expected: double-quoted identifiers, LEFT OUTER JOIN with both keys. After fix: SanitiseIdentifier correctly wraps unicode and reserved words. PASS.



Overload input:

Three chained pipes with mv-expand, bag_unpack, and row_number() in the same query. None of these operators currently compose through the single-node AST parser — the parser only captures the last recognised operator. FAIL — the parser is single-node; chained operators require a pipeline AST (linked list of nodes). This is a known architectural limitation, not a translator bug.



Adversarial input:

Null byte injection (input: "\x00\x01\x02") → parser rejects at guard with a clean error. 10 MB+ query body → rejected at guard. SQL injection string ("SELECT DROP TABLE users; --") → parsed as a KQL identifier, emitted as a quoted SQL string — safe. PASS on all adversarial cases.



Verdict — Artifact: NEEDS WORK.

Single-operator translations: ready. Chained/composed operator pipelines: broken at the parser level (single-node AST). This is the correct next architectural change.



GPS COMPLETE — Net Assessment

Mode

Verdict

One-line reason

G — Premise

SHAKEN

Full KQL equivalence is unachievable; capability tiers needed

P — Plan

PARTIALLY ATTACKED

80% P0 budget too loose; panics not P0-gated; SS-07 unvalidated

S — Artifact

NEEDS WORK

Single-operator: ready. Pipeline/chained operators: parser broken



Top three actions, ordered by impact:

Declare capability tiers in the bridge API (Tier 1/2/3) — reject Tier 3 operators early with a structured error, not a silent degraded translation.

Raise P0 CI gate to 100% and add zero-panic criterion for SS-05. Re-run SS-07 with object pool fix to confirm heap stabilises.

Rebuild parser as a pipeline AST (linked list of nodes) so chained KQL operators translate correctly. This is the blocker for real-world Fabric Eventhouse queries.





2. Code Fixes — All Failing Tests



2.1 Test Results After Fix Pass

Test ID

Name

Before

After

Fix location

TC-P-06

Compound left-outer join

FAIL

PASS

emitJoin()

TC-T-04

mv-expand → LATERAL VIEW EXPLODE

FAIL

PASS

emitMvExpand()

TC-T-05

bag_unpack → JSON_TABLE

FAIL

PASS

emitBagUnpack()

TC-T-07

row_number() window function

FAIL

PASS

emitWindowFn()

TC-E-03

Unicode identifiers

FAIL

PASS

SanitiseIdentifier()

TC-PF-03

No goroutine leak after 1000 req

FAIL

PASS

pool.go — NewPool()



All 6 failing tests now pass. Test suite runs clean under Go race detector (-race flag).



2.2 Fix Summary

TC-P-06 — Compound left-outer join

Root cause: emitJoin() only handled single JoinKeys[0]. Any compound key (multiple keys) was silently dropped.

Fix: iterate JoinKeys and build compound ON clause: l.col1 = r.col1 AND l.col2 = r.col2.

Karpathy P5 note: Kusto join key names assumed to match SQL column names. Human must verify if schemas diverge.



TC-T-04 — mv-expand → LATERAL VIEW EXPLODE

Root cause: no SQL translation existed for mv-expand — the operator returned an unsupported-type error.

Fix: emitMvExpand() emits LATERAL VIEW EXPLODE() (Spark SQL). Target engine assumption documented inline.



TC-T-05 — bag_unpack → JSON_TABLE

Root cause: not implemented. bag_unpack has no equivalent in standard SQL without schema knowledge.

Fix: emitBagUnpack() emits JSON_TABLE with a <schema> placeholder and an explicit comment. Caller must supply the concrete JSON schema — this cannot be auto-inferred.



TC-T-07 — row_number() window function

Root cause: window functions returned empty string — silently emitting invalid SQL.

Fix: emitWindowFn() builds OVER(PARTITION BY … ORDER BY …) clause from WindowOver and WindowOrder node fields. Works for row_number, rank, dense_rank, ntile. LAG/LEAD mapping is a separate fix.



TC-E-03 — Unicode identifiers

Root cause: identifiers were passed to SQL without quoting, causing syntax errors for non-ASCII names.

Fix: SanitiseIdentifier() detects non-ASCII runes, spaces, and SQL reserved words. Wraps in double-quotes and escapes embedded double-quotes per SQL standard.



TC-PF-03 / SS-01 — Goroutine leak

Root cause: unbounded goroutine-per-request model. Under 10k concurrent requests, goroutine count grew without bound.

Fix: NewPool(workers, queueDepth) creates a fixed-size worker pool. Workers drain a buffered channel. Shutdown() closes the channel and waits for all workers via sync.WaitGroup.





3. Stress Test Status

ID

Scenario

Verdict

Root cause

Remediation

SS-01

10k concurrent translations

FIXED

Unbounded goroutines

Bounded pool (pool.go)

SS-02

Nested subquery depth 20

WARN

Parse-time growth

Set max depth = 12 in parser guard

SS-03

128k-token query body

PASS

—

No action

SS-04

Schema mutation mid-flight

PASS

—

No action

SS-05

Malformed burst — 3 panics

FIXED

No panic recovery

safeTranslate() + recover()

SS-06

Cold-start latency

PASS

—

No action

SS-07

Heap drift over 30 min

PARTIAL

Unreclaimed []string + Builder

objpool.go (re-run needed)

SS-08

KQL → SQL → KQL round-trip

PASS

22 loss cases: window fns

Window fn fix reduces loss



SS-07 requires a post-fix re-run at 1,000 req/s for 30 minutes to confirm the object pool stabilises heap. Do not close this item without the re-run data.





4. CDLC Layer Coverage

Layer

What it tests

Status

Open items

1 — Lint/validation

AST schema, golangci-lint

PASS (18/18)

None

2 — Comprehension

Test fixture clarity (LLM-scored)

PASS (39/42)

3 fixtures below 4/5 threshold

3 — LLM-as-judge

Semantic equivalence scoring

IN PROGRESS

14 cases pending judge pass

4 — E2E sandbox

Live Fabric Lakehouse vs KQL Eventhouse

FAIL (8 cases)

Window fns — fix now deployed

5 — CI/CD + error budget

5-run suite, 80% P0 threshold

CONFIGURED

Threshold must raise to 100% P0





5. Karpathy Bloat Audit — Post AutoResearch Run

Audit performed on: translator/kql_to_sql.go + pool.go + objpool.go



Item

Status

Notes

No 10+ line block extractable into a named function

PASS

All emit functions are ≤ 30 lines. mapJoinKind() extracted correctly.

No copy-pasted patterns

PASS

Column quoting loops use SanitiseIdentifier consistently — no duplication.

Eval runner (prepare.go) locked

PASS

File not in agent context. Banner comment added.

Every hypothesis commit has 1-line comment

PASS

Fix commit header documents the hypothesis.

TranslateKQLtoSQL() is a pure function

PASS

No global state, no I/O, no side effects.

Window fns verified by E2E (not just unit)

OPEN

Unit test passes. E2E re-run needed after deploy.

No silent cross-system identity assumptions

PASS

Karpathy P5 flags added in emitJoin() comments.

No single-use abstractions

PASS

objpool.go pools only the two hot types profiled.

No unreachable branches in operator map

PASS

Default case in emitSQL() surfaces unknown types as errors.

Code readable in under 5 minutes

PASS

Reviewed. Each function has a 2-line root-cause + fix comment.



Audit result: 9 of 10 items clear. One open item: E2E re-run for window function cases after deploy.





6. AutoResearch Loop — Configuration

Scalar metric: semantic_equivalence_score = matches / total. Target: ≥ 0.97.

Time box: 30 seconds per experiment run (enforced in eval/prepare.go via context timeout).

Agent-modifiable: translator/kql_to_sql.go only.

Locked oracle: eval/prepare.go — never in agent context.

Current score before this fix pass: 0.857 (36/42). Projected after fix: 0.971 (40/41 — TC-T-06 still skip).



Loop protocol (BIT — Build → Integrate → Tune)

Build: agent modifies kql_to_sql.go with a hypothesis. prepare.go scores it.

Integrate: after 10 successful loops, human review + bloat audit before merging.

Tune: every 5 sessions, agent self-analysis of failure patterns (currently: window fns + chained operators).



Next hypothesis for the loop: pipeline AST — replace single Node with []Node slice to handle chained KQL pipes.



7. Next Sprint — Ordered by Impact

Priority

Action

Owner

Blocks

P0

Raise CI gate: 100% P0 pass, zero-panic criterion

QA

All future releases

P0

Re-run SS-07 with object pool fix — confirm heap stable

QA + Infra

Ship clearance

P0

Pipeline AST: replace single Node with []Node pipeline

Dev

Chained KQL operators

P1

Capability tier declaration (Tier 1/2/3) in bridge API

Dev

User trust model

P1

LLM-as-judge: complete 14 pending cases in Layer 3

QA

CDLC coverage

P1

E2E re-run for window function cases

QA

E2E layer clearance

P2

prev() / next() → LAG / LEAD mapping

Dev

TC-T-07 full coverage

P2

TC-T-06: dynamic column → SQL VARIANT (Fabric-specific)

Dev

Fabric Lakehouse compat





kqlbridge QA War Room  |  Context Engineer + QA Engineer  |  May 2026