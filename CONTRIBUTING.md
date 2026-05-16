# Contributing to KQLBridge

Thank you for wanting to improve KQLBridge. Before opening a PR, read this document.

---

## The One Non-Negotiable Rule

**Every contribution must include a test case in `tests/eval/benchmark.json`.**

No test case = no merge. This is not negotiable.

The eval harness is the single source of truth for this project.
If you found a bug, the proof is a failing test case.
If you implemented a feature, the proof is a passing test case.

---

## Locked Files

These files are **never modified by contributors** — only by maintainers:

```
tests/eval/prepare.py       # Eval oracle — LOCKED
tests/eval/benchmark.json   # 100 benchmark queries — LOCKED (maintainer adds cases)
src/kqlbridge/ast_nodes.py  # AST type definitions — LOCKED
src/kqlbridge/grammar/kql.lark  # Grammar — LOCKED
src/kqlbridge/semantic.py   # Semantic validator — LOCKED
```

PRs that modify locked files will be rejected. CI enforces this automatically.

---

## What You Can Contribute

**Open for contribution:**
- `src/kqlbridge/parser.py` — improving KQL → AST parsing
- `src/kqlbridge/generators/spark_sql.py` — improving AST → Spark SQL generation
- `src/kqlbridge/generators/tsql.py` — T-SQL generator (v0.2)
- `context/` — improving CDLC operator skill files
- `docs/` — improving documentation
- `examples/` — adding real-world migration examples

---

## How to Contribute

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/kqlbridge
cd kqlbridge

# 2. Install in dev mode
pip install -e ".[dev]"
pip install sqlglot

# 3. Run the baseline eval
python tests/eval/prepare.py
# Record your baseline score

# 4. Make your changes to parser.py or generators/spark_sql.py

# 5. Write unit tests
pytest tests/test_operators.py -v

# 6. Confirm your change improves the eval score
python tests/eval/prepare.py
# Score must not regress

# 7. Add a test case to benchmark.json (maintainer will review and add formally)
# Open an issue with your test case in the format:
# {"id": "std_NNN", "category": "standard", "description": "...", "kql": "...", "expected_sql": "..."}

# 8. Submit PR with:
# - Description of which benchmark case(s) you fixed
# - Before/after eval score
# - Any edge cases you discovered
```

---

## Bug Reports

If you find a KQL query that KQLBridge translates incorrectly:

1. Open an issue with the template:
   ```
   **KQL input:** `AppLogs | where ...`
   **KQLBridge output:** `SELECT ...`
   **Expected output:** `SELECT ...`
   **What's wrong:** [explain the semantic difference]
   ```

2. Include the Spark SQL dialect — the expected SQL must be runnable on Databricks or Fabric Spark.

3. The maintainer will add a failing test case to `benchmark.json` and confirm the issue.

---

## Code Style

- Follow the existing style in `parser.py` and `spark_sql.py`
- One method per operator — do not merge operators into shared helpers until the pattern appears ≥ 3 times
- Do not refactor adjacent passing code while fixing a failing operator
- Every change should be traceable to a benchmark case ID (mention it in the commit message)

---

## License

By contributing, you agree your contributions are licensed under Apache 2.0.
