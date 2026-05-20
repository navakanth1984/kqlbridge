# Debugging and Jules Integration Guide

Welcome to the **KQLBridge** debugging and integration guide. This document explains how to set up local debugging, inspect intermediate AST structures, and integrate with autonomous agents or test frameworks (like **Jules**) using the `.jules` diagnostic log system.

---

## 1. Jules Diagnostic Logging System (`.jules/`)

`kqlbridge` includes an automated stress-testing harness (`run_stress_test.py`) that monitors parser and translation compliance against a battery of real-world, complex, and adversarial KQL queries.

### Failure Capture Mechanism
When `run_stress_test.py` encounters any translation error or parser crash:
1. It automatically isolates the failure.
2. It generates a markdown diagnostics log in the `.jules/` directory.
3. The generated log format is fully optimized for consumption by developers and AI agents (like Jules):

```markdown
# FAILURE: Complex Filtering and Extend

**KQL:**
```kusto
SecurityEvents
| where TimeGenerated > ago(7d) and (Level == 'Error' or (Level == 'Warning' and Message has 'timeout'))
| extend is_critical = iff(Level == 'Error', true, false)
| project TimeGenerated, is_critical
```

**Traceback:**
```python
Traceback (most recent call last):
  File "C:\Users\navka\navakanth001\kqlbridge\run_stress_test.py", line 131, in run
    _, pyspark_code = smart_transpile(kql.strip(), force_engine="pyspark")
  ...
AttributeError: 'str' object has no attribute 'table_name'
```
```

> [!TIP]
> **Jules development loop:** When developing new features, run `py run_stress_test.py` to populate `.jules/` with any active regression logs. Your AI agent or test suite can scan this folder to pinpoint exactly which files, operators, or semantic nodes require correction.

---

## 2. Interactive CLI Debugging

The command-line interface provides immediate feedback on translation logic:

### Translate Queries Interactively
```bash
# Compile KQL to Spark SQL (default)
kqlbridge translate "SecurityEvents | where Level == 'Error' | count"

# Compile KQL to T-SQL (Fabric SQL Warehouse)
kqlbridge translate "SecurityEvents | take 100" --tsql
```

### Validate Syntax (CI/CD Gates)
```bash
# Exits with status 0 if fully supported, 1 if unsupported or invalid syntax
kqlbridge check "SecurityEvents | where isnull(Level)"
```

---

## 3. Parsing and Lark AST Inspection

To debug AST construction or grammar parsing errors, you can run a Python script to interactively parse any query and print the raw AST.

### Pretty Print Lark Parse Tree
Create a temporary scratch script or run in a python REPL:

```python
from kqlbridge.parser import parse

# Parse KQL query to AST
ast = parse("SecurityEvents | where Level == 'Error' | project TimeGenerated")
print(ast.pretty())
```

> [!NOTE]
> Under the hood, `kqlbridge` uses [Lark](https://github.com/lark-parser/lark) with the locked grammar file [kql.lark](file:///c:/Users/navka/navakanth001/kqlbridge/src/kqlbridge/grammar/kql.lark). If a query fails during token matching, the Lark exception will indicate the exact character, line, column, and the list of expected grammar terminals.

---

## 4. IDE Debugging Setup (VS Code)

To set up native step-by-step debugging inside VS Code, add the following configuration to your `.vscode/launch.json` file. This lets you set breakpoints inside `parser.py` or `generators/spark_sql.py` and step through translations or test suites.

### VS Code `launch.json`
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Pytest (All)",
            "type": "debugpy",
            "request": "launch",
            "module": "pytest",
            "args": [
                "-v",
                "${workspaceFolder}/tests"
            ],
            "console": "integratedTerminal",
            "justMyCode": true
        },
        {
            "name": "Debug Single Stress Test",
            "type": "debugpy",
            "request": "launch",
            "module": "pytest",
            "args": [
                "-v",
                "${file}"
            ],
            "console": "integratedTerminal",
            "justMyCode": false
        },
        {
            "name": "Run & Debug Stress Harness",
            "type": "debugpy",
            "request": "launch",
            "program": "${workspaceFolder}/run_stress_test.py",
            "console": "integratedTerminal",
            "justMyCode": false
        }
    ]
}
```

---

## 5. Adversarial Score Verification (`prepare.py`)

KQLBridge maintains an **adversarial, Sentinel, edge-case, and standard** test suite to prevent regressions or compiler injection vulnerability hazards.

To verify your scores locally before committing or deploying:
```bash
py tests/eval/prepare.py
```

> [!IMPORTANT]
> The target adversarial score must be **100.0%** to guarantee absolute safety against SQL injection payloads (e.g. raw subquery recursive injections or path manipulation).

---

## 6. Real-time Debugging Logs

If you need verbose logs while translating:
```python
import logging
from kqlbridge import translate

logging.basicConfig(level=logging.DEBUG)
sql = translate("T | where Value > 10")
```
This logs intermediate parser steps, token groupings, and engine selection queries.
