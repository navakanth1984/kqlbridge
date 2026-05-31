# AGENTS.md  -  kqlbridge

> KQL -> Spark SQL / T-SQL transpiler for Microsoft Fabric and Databricks

---

## Project Overview

kqlbridge is a Python library and CLI tool that transpiles Kusto Query Language (KQL)
queries to Spark SQL (for Microsoft Fabric / Databricks) and T-SQL (for Microsoft Fabric
SQL analytics endpoints). It enables data engineers to reuse KQL analytics logic across
the full Microsoft Fabric and Azure data platform without manual rewriting.

**Active development**  -  ADR-driven architecture, stress-tested to production limits.

---

## Repository Structure

```
src/kqlbridge/        Core transpiler package
  parser.py           KQL parser (nesting depth limit: 500 levels enforced)
  smart.py            Smart transpilation layer
  generators/
    spark_sql.py      Spark SQL code generator (SerializeOp limits enforced)
    tsql.py           T-SQL code generator
tests/                Unit and integration tests
docs/                 API docs, usage guides
examples/             Sample KQL queries and expected transpiled output
context/              Query context definitions (schema, catalog)
scripts/              Dev helpers  -  jules_sync.py, supreme_agentic_stress.py, ulcop_monitor.py
logs/                 Transpiler execution logs (transcript.jsonl for session replay)
graphify-out/         Codebase graph analysis (auto-generated  -  READ before coding)
.github/              CI workflows
.jules/               Jules task history and automated memory
```

Key files:
- `pyproject.toml`  -  package build config
- `kqlbridge_arch_adr.md`  -  Architecture Decision Records (READ FIRST for major changes)
- `implementation_plan.md`  -  active implementation plan artifact
- `task.md`  -  current task checklist artifact (keep updated)
- `walkthrough.md`  -  session history and achievements log
- `ROADMAP.md`  -  planned operator support and milestones
- `operator_status.md`  -  current transpilation coverage per KQL operator
- `kqlbridge_stress_audit_report.md`  -  compiler-grade stress audit results
- `stress_test.sql`  -  stress test queries used for regression testing
- `run_stress_test.py`  -  stress test runner (use uv: `uv run run_stress_test.py`)
- `scripts/supreme_agentic_stress.py`  -  full stress suite runner
- `scripts/ulcop_monitor.py`  -  transpiler monitoring and telemetry
- `scripts/jules_sync.py`  -  Jules context sync utility
- `CATEGORY_REPAIR_GUIDE.md`  -  operator category repair procedures
- `CODEOWNERS`  -  code ownership by module (follow for review routing)

---

## Tech Stack

- **Language**: Python 3.11+
- **Build**: `pyproject.toml` (PEP 621)
- **Runner**: `uv` (preferred for speed  -  use `uv run` for scripts)
- **Testing**: pytest
- **Linting**: ruff (configured in `pyproject.toml`)
- **Architecture tracking**: ADR markdown files in root

---

## Established Performance Benchmarks

These are verified baselines from `kqlbridge_stress_audit_report.md`. Do not regress them.

| Benchmark | Baseline | Test Method |
|---|---|---|
| Nesting depth | 800 nested iff() parsed successfully | preprocessed desugaring |
| Thread concurrency | 640 threads, zero memory leaks | supreme_agentic_stress.py |
| Throughput | 235.4 queries/second | global parser instance caching |

Any parser-level or generator-level change must be validated against these baselines
before merging. Run: `uv run scripts/supreme_agentic_stress.py`

---

## Established Parser Safety Limits

These safeguards are live in the codebase. Do not weaken them without an ADR.

- **parser.py L296-298**: Nesting depth limit of 500 for parenthesized expressions.
  Raises an exception on expressions exceeding this depth.
- **spark_sql.py L180-182**: SerializeOp structured limit  -  directs developers to
  use `order by` window partitioning instead of unbounded serialize chains.

---

## KQL Operator Coverage

Current operator status is tracked in `operator_status.md`. Before implementing
a new operator or fixing a transpilation, check:
1. Is it tracked in `operator_status.md`? Update it after your fix.
2. Is there an open issue for it? Reference it in the PR.
3. Does it appear in `stress_test.sql`? Add a stress test case if not.

---

## Transpilation Targets

| Target     | Use Case                                   |
|------------|--------------------------------------------|
| Spark SQL  | Microsoft Fabric Notebooks, Databricks SQL |
| T-SQL      | Fabric SQL Analytics Endpoint, Synapse     |

KQL semantics with no direct equivalent (mv-expand, bag_unpack, make-series)
require documented approximations  -  see `kqlbridge_arch_adr.md`.

---

## Critical Rules

### Git Workflow  -  STRICT
- **NEVER use `git commit --no-verify`**. Pre-commit hooks exist for a reason.
  If a hook is failing, fix the underlying issue  -  do not bypass the hook.
- **NEVER push directly to main**. All changes go via a PR, even minor ones.
  Create a feature branch, open a PR, and wait for review.
- Commit messages must follow Conventional Commits:
  `type(scope): description` (e.g. `fix(parser): handle nested mv-expand`)
- Valid types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

### Correctness First
- Transpilation must be semantically correct, not just syntactically valid.
- Every operator implementation must include a test with at least:
  - A simple case
  - A null/empty input case
  - A nested/composed case
- Use `examples/` to document non-obvious transpilation decisions.

### Architecture
- Read `kqlbridge_arch_adr.md` AND `graphify-out/GRAPH_REPORT.md` before
  adding new parsing stages, IR nodes, or target backends.
- New KQL operators must be categorised following `CATEGORY_REPAIR_GUIDE.md`.
- Do not break the operator registry pattern  -  all operators must self-register.
- New major features require an entry in `implementation_plan.md` first.

### Tests
- Run tests before every commit: `python -m pytest tests/ -v`
- Run stress tests for any parser-level change: `uv run scripts/supreme_agentic_stress.py`
- Do not regress the benchmarks in `kqlbridge_stress_audit_report.md`.
- Regressions in `stress_test.sql` are blocking  -  do not merge.

### Code Style
- Follow ruff configuration in `pyproject.toml`.
- Type hints required on all public functions.
- Docstrings in Google style format.

### Artifacts  -  Keep Updated
After every task session, update these artifacts to reflect current state:
- `task.md`  -  check off completed items, add new ones
- `walkthrough.md`  -  append a summary of the session's achievements
- `operator_status.md`  -  if any operator coverage changed

---

## Build & Run

```bash
# Install in dev mode
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Run stress suite (preferred: use uv for speed)
uv run scripts/supreme_agentic_stress.py

# Run stress tests (legacy)
python run_stress_test.py

# Transpile a single query (CLI)
kqlbridge "TableName | where Timestamp > ago(1d) | summarize count() by bin(Timestamp, 1h)" --target spark

# Transpile to T-SQL
kqlbridge "TableName | take 100" --target tsql
```

---

## Jules-Specific Guidance

- `.jules/` directory exists  -  Jules has active task history and automated memory for this repo.
- Read `graphify-out/GRAPH_REPORT.md` first on any session involving structural changes.
- Read `implementation_plan.md` to understand the approved direction before starting.
- Always check `operator_status.md` before starting any operator-related task.
- When fixing an operator, update: `src/`, `tests/`, `operator_status.md`, `examples/` in one PR.
- Use `uv run` for all script execution  -  faster than plain `python`.
- `context/` holds schema/catalog context for type-aware transpilation  -  use it.
- `CODEOWNERS` defines review requirements  -  tag the right owner on PRs.
- For performance-impacting changes, verify against benchmarks in `kqlbridge_stress_audit_report.md`.
- Subagents spawned for deep audits must be explicitly terminated after task completion.
- **DO NOT use `--no-verify` on any commit. Ever.**
- **DO NOT push directly to main. Open a PR.**
