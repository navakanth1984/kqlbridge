# KQLBridge

**KQL → Spark SQL / T-SQL transpiler for Microsoft Fabric and Databricks**

[![PyPI version](https://badge.fury.io/py/kqlbridge.svg)](https://badge.fury.io/py/kqlbridge)
[![Eval Score](https://img.shields.io/badge/eval-100%25-brightgreen)](tests/eval/prepare.py)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)

KQLBridge lets data engineers write queries in **Kusto Query Language (KQL)** and compile them to **Spark SQL** (Databricks, Microsoft Fabric Spark notebooks) or **T-SQL** (Fabric SQL Warehouse, Synapse Analytics).

```python
from kqlbridge import translate

kql = "AppLogs | where Level == 'Error' | summarize count() by ServiceName"
sql = translate(kql, target="spark")
# → SELECT ServiceName, COUNT(*) FROM AppLogs WHERE Level = 'Error' GROUP BY ServiceName
```

---

## Why KQLBridge?

Microsoft Fabric runs two query engines side by side: **Eventhouse** (KQL) and **Spark notebooks / SQL Warehouse** (Spark SQL / T-SQL). Teams that wrote years of KQL analytics can't simply copy-paste those queries into a Spark cell. KQLBridge automates the translation.

**Use cases:**
- Migrate ADX / Eventhouse KQL workloads to Databricks or Fabric Spark
- Build routing agents that pick the right engine per query at runtime
- Teach polyglot data engineering — learn one language, compile to all targets

---

## Installation

```bash
pip install kqlbridge
```

**Requires**: Python 3.10+, no external services, no API keys.

---

## Quick Start

```python
from kqlbridge import translate, detect_operators, is_supported

# Translate KQL to Spark SQL
sql = translate(
    "AppLogs | where TimeGenerated > ago(24h) | project Message, Level",
    target="spark"
)

# Check which operators are used
ops = detect_operators("AppLogs | where Level == 'Error' | summarize count() by Host")
# → ['where', 'summarize']

# Check if a query is fully translatable
if is_supported("AppLogs | make-series count() on TimeGenerated"):
    sql = translate(...)
else:
    print("Unsupported operators — keep in KQL engine")
```

---

## Supported Operators (v0.1)

| KQL Operator | Spark SQL Output | Status |
|---|---|---|
| `where` | `WHERE clause` | ✅ v0.1 |
| `project` | `SELECT columns` | ✅ v0.1 |
| `summarize count()` | `SELECT COUNT(*) GROUP BY` | ✅ v0.1 |
| `summarize sum/avg/min/max` | Aggregation functions | ✅ v0.1 |
| `bin(col, 1h)` | `DATE_TRUNC('hour', col)` | ✅ v0.1 |
| `ago(1h)` | `CURRENT_TIMESTAMP - INTERVAL '1 hours'` | ✅ v0.1 |
| `extend` | `SELECT *, expr AS alias` | ✅ v0.1 |
| `order by` / `sort by` | `ORDER BY col ASC/DESC` | ✅ v0.1 |
| `take` / `limit` | `LIMIT n` | ✅ v0.1 |
| `distinct` | `SELECT DISTINCT` | ✅ v0.1 |
| `join` (inner) | `INNER JOIN ON key` | ✅ v0.1 |
| `union` | `UNION ALL` | ✅ v0.1 |
| `let` variables | CTEs (`WITH … AS`) | ✅ v0.1 |
| `count()` | `COUNT(*)` scalar | ✅ v0.1 |

See [supported_operators.md](docs/supported_operators.md) for full reference.
See [unsupported_operators.md](docs/unsupported_operators.md) for operators with no SQL equivalent.

---

## Eval Score

KQLBridge measures accuracy against a **locked 100-query benchmark** (70 standard, 20 edge-case, 10 adversarial). The eval script is the single source of truth — it is never modified by the agent loop.

```bash
python tests/eval/prepare.py
# SCORE: 85.0% (85/100)
```

---

## Architecture

```
KQL input
  → Lark lexer (LOCKED grammar: kql.lark)
  → Parser (MODIFIABLE: parser.py)
  → AST nodes (LOCKED: ast_nodes.py)
  → Semantic check (LOCKED: semantic.py)
  → Generator (MODIFIABLE: generators/spark_sql.py)
  → Spark SQL / T-SQL output
```

**Locked files** (oracle, grammar, types) are never touched by the agentic build loop.
**Modifiable files** (parser, generators) are where improvements happen.

---

## Contributing

All contributions must include a corresponding test case in `tests/eval/benchmark.json`.
PRs that do not include a new test case will not be merged.

```bash
git clone https://github.com/navakanth1984/kqlbridge
cd kqlbridge
pip install -e ".[dev]"
python tests/eval/prepare.py  # baseline score
pytest tests/                 # unit tests
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines.

---

## Companion Projects

- **PipeQL** — Pipe-first SQL syntax that compiles to the same Spark SQL target (v0.2 roadmap)
- **DE-Context Kit** — Routing agent + CDLC skill packages using KQLBridge under the hood

---

## License

Apache 2.0. See [LICENSE](LICENSE).
