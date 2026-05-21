<!-- converted from kqlbridge_arch_adr.docx -->

kqlbridge
Architecture Decision Record
Developer / Architect  +  QA Engineer  |  GPS Framework as governing ring
May 2026  |  Post QA War Room Report


# 1. GPS as the governing ring
The GPS framework (Gaslight → Pushback → Stress-test) is not a pre-ship ceremony in this architecture. It is the commit boundary between every Developer/Architect decision and every QA validation gate. Neither role ships without passing through G → P → S.


The ring is bidirectional: Developer/Architect and QA Engineer each run GPS on the OTHER role's outputs. The Architect's design is stress-tested by QA before implementation. The QA test plan is gaslighted by the Architect before it runs against production. This prevents both roles from optimising within their own frame.


# 2. GPS run on this architecture
## G — Premise: pipeline AST + capability tiers solves the right problem
Inverted argument: "What if the correct solution is not a bridge at all, but a native SQL-first Fabric connector that bypasses KQL entirely?"
Evidence for inversion: Fabric Lakehouse already exposes a SQL endpoint. If the end-user need is SQL analytics on Eventhouse data, the bridge adds a translation layer that is never zero-cost. The 2.2% round-trip loss (SS-08) and the 8 E2E failures confirm this is not lossless.
Counter-evidence that held the premise: the bridge's value is not lossless translation — it is incremental migration. Organisations with existing KQL asset libraries (notebooks, dashboards, alerting rules) cannot rewrite them overnight. The bridge converts KQL queries programmatically during the migration window. The tiers system makes the capability boundary explicit so users know what to migrate manually.
Verdict: G HELD — with the tier system declared, the premise is honest. The bridge is a migration tool, not a production replacement. This reframing is the G gate's core output.

## P — Plan: three architectural decisions pushed back on
Pushback 1 — CTE flattening does not handle join-inside-pipeline.
The Architect's plan to flatten all Tier 1 pipelines to a single SELECT fails when a join stage appears alongside a summarize in the same pipeline (structural conflict). Fix: the flattening translator detects this case, returns a descriptive error, and escalates to the CTE path. This is not a bug — it is an architectural boundary made explicit. Tested in TestTranslatePipeline_Tier1Flat (join-in-pipeline path).

Pushback 2 — SchemaHint ownership is undefined without a caller contract.
Tier 2 operators require schema knowledge the bridge cannot infer. Without an explicit caller contract, every Tier 2 translation silently emits a placeholder (<schema>) that crashes at runtime. Fix: SchemaHint struct with JSONFields and ArrayElementType maps is the explicit contract. Tier 2 translations without a hint emit a commented placeholder — visible and actionable, not silent.

Pushback 3 — 15 tests passing does not prove correctness of the translation semantics.
String-match tests confirm structural output, not semantic equivalence. The LLM-as-judge layer (CDLC Layer 3) must be completed for the 14 remaining cases before the semantic_equivalence_score is meaningful. The AutoResearch loop must not be run against a score that is measuring string structure instead of query semantics.
Verdict: P PARTIALLY ATTACKED — all three pushbacks have explicit mitigations in the implementation. None are blocking, all are tracked.

## S — Stress-test: architecture under adversarial conditions
Standard: "Events | where level == 'error' | summarize count() by category | order by count_ desc | take 50" → single flat SQL, Tier 1, 0 CTEs. PASS.
Edge: pipe inside string literal "T | where name == 'a|b' | take 10" → 3 stages (not 4). PASS.
Overload: 20-stage pipeline with alternating Tier1/Tier2 stages → CTE chain with 20 CTEs, correct Tier2 escalation, all warnings populated. PASS.
Adversarial: Tier 3 operator inside a Tier 1 pipeline → CapabilityError at parse time, never reaches translator. PASS. Null byte → rejected at guard. Malformed JSON in bag_unpack hint → placeholder emitted with comment. PASS.
Verdict: S NEEDS WORK — one known gap: join-inside-pipeline falls through to a CTE path that does not yet exist. The translator returns a descriptive error. This is the correct behaviour (fail loudly) but the CTE join path must be built in the next sprint.

GPS NET ASSESSMENT — Architecture


# 3. Architectural decisions
## ADR-01: Pipeline AST — []Node chain replaces single *Node
Status: IMPLEMENTED. All tests green.
Decision: KQL's pipe-chained semantics require a sequence of nodes. The single-node parser captured only the last operator in a chain, silently dropping all preceding operators. The pipeline parser (parser/pipeline.go) splits on | with respect to string literals and parentheses, parses each stage into a typed Node, and returns a Pipeline{Stages: []*Node}.
GPS G gate result: held. Pipeline AST is the correct representation for a pipe-chained language.
Karpathy P1: assumptions explicit — Stage 0 is always the source table. Subsequent stages are operators.

## ADR-02: Capability Tier system (Tier 1 / 2 / 3)
Status: IMPLEMENTED. Tier classification is the single source of truth in translator/tier.go.
Tier 1: flat SQL, no schema assumptions. Tier 2: partial, caller supplies SchemaHint. Tier 3: rejected at parse time with CapabilityError (operator name, stage index, explanation, alternative).
GPS G gate result: held (reframed). The bridge is a migration tool. Tiers make capability boundaries explicit and honest.
GPS P gate result: SchemaHint ownership contract defined — caller owns schema knowledge, bridge owns translation.

## ADR-03: Flattening translator + CTE chain for Tier 2
Status: IMPLEMENTED. Join-in-pipeline CTE path deferred to next sprint.
Tier 1 pipelines: flattened to a single SQL SELECT (WHERE + GROUP BY + ORDER BY + LIMIT composed from pipeline stages). Tier 2 pipelines: CTE chain (WITH cte_0 AS (...), cte_1 AS (...) SELECT * FROM cte_n). Mixed pipelines: Tier2 stages escalate the whole pipeline to CTE mode.
Dialect support: Spark SQL (LATERAL VIEW EXPLODE), ANSI/DuckDB (UNNEST), Fabric (Spark-compatible). Dialect declared in SchemaHint.TargetDialect.

## ADR-04: CI gate hardened to 100% P0 + zero-panic criterion
Status: IMPLEMENTED (eval/prepare_v2.go).
GPS P finding: 80% P0 error budget is wrong for deterministic code translation. The bridge produces the same SQL for the same KQL every time — non-determinism lives only in the LLM-as-judge (Layer 3). Separate GatePolicy structs for production layers (100% P0, zero panics) and LLM judge layer (80%, non-deterministic).

## ADR-05: SS-07 heap stability harness (eval/ss07_harness.go)
Status: IMPLEMENTED. Re-run required before closing the WARN.
Accept criterion: heap growth < 5% per 10-minute window above baseline at 1,000 req/s sustained. Short CI proxy: SS07_DURATION_SECONDS=60 runs a 60-second proxy with 10% growth threshold. The harness uses the bounded pool (pool.go) and object pool (objpool.go) — both deployed in the previous fix pass.


# 4. Complete test ledger — after architecture pass


# 5. Next sprint — GPS-gated delivery plan

GPS ring reminder: every item above has a GPS G gate before any code is written, and a GPS S gate before any merge is approved. QA Engineer runs GPS S on the Developer/Architect's output. Developer/Architect runs GPS G on the QA Engineer's test plan. The ring is bidirectional.
| Role | GPS G invoked when | GPS P invoked when | GPS S invoked when |
| --- | --- | --- | --- |
| Developer / Architect | Before any design decision locks (AST shape, tier model, CTE strategy) | After design, before first line of code — force explicit tradeoff naming | Before merge — stress the architecture under 20-stage pipelines, adversarial inputs |
| QA Engineer | Before writing test cases — invert the test premise | After test plan drafted, before test cases written — push back on coverage claims | Before any stress test is closed — run the actual artifact under load, not a model of it |
| Mode | Verdict | Implication |
| --- | --- | --- |
| G — Premise | HELD (reframed) | Bridge = migration tool, not production replacement. Capability tiers make the boundary honest. |
| P — Plan | PARTIALLY ATTACKED | 3 pushbacks mitigated. LLM-judge completion is the open gate before AutoResearch loop runs. |
| S — Artifact | NEEDS WORK | Join-in-pipeline CTE path missing. All other GPS S cases pass. Next sprint item. |
| Test ID | Description | Type | Status | GPS gate |
| --- | --- | --- | --- | --- |
| TC-P-06 | Compound left-outer join | Unit | PASS | S |
| TC-T-04 | mv-expand → LATERAL VIEW EXPLODE | Unit | PASS | S |
| TC-T-05 | bag_unpack → JSON_TABLE | Unit | PASS | S |
| TC-T-07 | row_number() window function | Unit | PASS | S |
| TC-E-03 | Unicode identifiers | Unit | PASS | S |
| TC-PF-03 | No goroutine leak after 1000 req | Unit | PASS | S |
| Tier-01 | Tier 1 operator classification | Unit | PASS | P |
| Tier-02 | Tier 2 operator classification | Unit | PASS | P |
| Tier-03 | Max-tier-wins for mixed pipeline | Unit | PASS | P |
| Pipeline-01 | Simple 4-stage chain parse | Unit | PASS | G |
| Pipeline-02 | Pipe inside string literal (adversarial) | Unit | PASS | S |
| Pipeline-03 | Empty stage error | Unit | PASS | S |
| Pipeline-04 | Null byte rejected at guard | Unit | PASS | S |
| Pipeline-05 | Tier3 reject at parse time | Unit | PASS | G |
| Trans-01 | Tier 1 flat SQL (filter+project+order+take) | Unit | PASS | S |
| Trans-02 | Tier 1 summarize → GROUP BY | Unit | PASS | S |
| Trans-03 | Tier 2 mv-expand Spark dialect | Unit | PASS | S |
| Trans-04 | Tier 2 bag_unpack with SchemaHint | Unit | PASS | S |
| Trans-05 | Tier 2 mv-expand DuckDB dialect | Unit | PASS | S |
| Trans-06 | Nil pipeline error | Unit | PASS | S |
| Trans-07 | Empty pipeline error | Unit | PASS | S |
| SS-01 | 10k concurrent — goroutine leak | Stress | FIXED | S |
| SS-05 | Malformed burst — panics | Stress | FIXED | S |
| SS-07 | Heap drift 30 min | Stress | OPEN — re-run | S |
| E2E-WF | Window fn E2E re-run | E2E | OPEN — pending | S |
| Sprint item | GPS gate before start | GPS gate before merge | Owner |
| --- | --- | --- | --- |
| Join-in-pipeline CTE path (ADR-03 gap) | G: is CTE join better than subquery join? | S: join+summarize in same pipeline | Dev/Arch |
| LLM-as-judge complete (14 pending) | P: are judge prompts testing semantics, not syntax? | S: adversarial fixture injection into judge | QA Eng |
| SS-07 re-run with objpool fix | G: is the object pool the right root cause? | S: 30-min @ 1000 req/s, heap < 5% growth | QA Eng |
| E2E re-run on window function cases | G: could Fabric env config be the real cause? | S: run ×3, verify stability | QA Eng |
| Dialect registry (ADR-03 extension) | P: should dialects be plugins or enums? | S: unknown dialect must error cleanly | Dev/Arch |
| Capability tier API surface | G: does tier exposure help or confuse callers? | S: misuse of tier constants must error | Dev/Arch |