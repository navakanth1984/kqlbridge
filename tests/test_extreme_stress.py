"""
tests/test_extreme_stress.py — KQLBridge v0.11.1 Core Stress Testing Suite
========================================================================
Author: Senior QA Automation and Core Stress Testing Engineer

This suite performs aggressive stress testing across the following areas:
1. Thread Concurrency / Safety Sweep: 100+ concurrent translations using ThreadPoolExecutor.
2. Nested Window Scenarios: Nesting and inline expressions involving prev/next/toupper.
3. Sparse & Complex Schema Hint Validation: Dictionary types, sparse, and malformed hints.
4. PySpark Generator Projections: Complex pipelines with window functions mapping to selectExpr.
5. Multi-iteration runs under load.
"""

import pytest
import concurrent.futures
import random
from kqlbridge import translate, SchemaHint, WindowSpec

# Define baseline configurations for thread concurrency safety checks
CONCURRENCY_TEST_CASES = [
    {
        "kql": "AppLogs | serialize | extend prev_level = prev(Level)",
        "dialect": "spark",
        "hint": SchemaHint(window_spec=WindowSpec(partition_by=["Computer"], order_by=["TimeGenerated DESC"])),
        "expected_sub": ["LAG(Level) OVER (PARTITION BY Computer ORDER BY TimeGenerated DESC)"]
    },
    {
        "kql": "AppLogs | serialize | extend prev_level = prev(Level)",
        "dialect": "tsql",
        "hint": SchemaHint(window_spec=WindowSpec(partition_by=["Computer"], order_by=["TimeGenerated DESC"])),
        "expected_sub": ["LAG(Level) OVER (PARTITION BY Computer ORDER BY TimeGenerated DESC)"]
    },
    {
        "kql": "AppLogs | serialize | extend prev_level = prev(Level)",
        "dialect": "pyspark",
        "hint": SchemaHint(window_spec=WindowSpec(partition_by=["Computer"], order_by=["TimeGenerated DESC"])),
        "expected_sub": ["LAG(Level) OVER (PARTITION BY Computer ORDER BY TimeGenerated DESC)"]
    },
    {
        "kql": "AppLogs | take 10",
        "dialect": "tsql",
        "hint": None,
        "expected_sub": ["SELECT TOP 10", "FROM AppLogs"]
    },
    {
        "kql": "AppLogs | take 10",
        "dialect": "spark",
        "hint": None,
        "expected_sub": ["LIMIT 10"]
    },
    {
        "kql": "AppLogs | take 10",
        "dialect": "pyspark",
        "hint": None,
        "expected_sub": ["df.limit(10)"]
    },
    {
        "kql": "AppLogs | where Level == 'Error' | extend UpperMsg = toupper(Message)",
        "dialect": "spark",
        "hint": None,
        "expected_sub": ["WHERE Level = 'Error'", "UPPER(Message) AS UpperMsg"]
    }
]


class TestConcurrencyAndThreadSafety:
    """Thread safety validation with 100+ concurrent translation tasks."""

    @pytest.mark.parametrize("iteration", range(3))
    def test_concurrent_translation_sweeps(self, iteration):
        """Run 100+ concurrent translations under high load to detect shared-state leaks or contamination."""
        num_tasks = 120
        tasks = []
        for i in range(num_tasks):
            case = random.choice(CONCURRENCY_TEST_CASES)
            tasks.append((case["kql"], case["dialect"], case["hint"], case["expected_sub"]))

        errors = []

        def worker(kql, dialect, hint, expected_sub):
            try:
                result = translate(kql, target=dialect, hint=hint)
                # Verify that the generated output is not contaminated and contains expected elements
                for sub in expected_sub:
                    assert sub in result, f"Expected substring {sub!r} not found in output: {result!r}"
                return True
            except Exception as e:
                errors.append(f"Failure in translating {kql!r} to {dialect!r}: {type(e).__name__}: {e}")
                return False

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            futures = [executor.submit(worker, *t) for t in tasks]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert not errors, f"Concurrency test failed with {len(errors)} errors:\n" + "\n".join(errors[:5])
        assert all(results), "Not all threads successfully processed their translations."


class TestNestedWindowScenarios:
    """Nested windowing, string manipulation inside windowing, and arithmetic on window results."""

    def test_nested_window_calls(self):
        """Verify parsing and rendering of deeply nested window functions."""
        # prev(next(prev(Level)))
        kql_nest1 = "AppLogs | serialize | extend x = prev(next(prev(Level)))"
        res_spark1 = translate(kql_nest1, target="spark")
        assert "LAG(LEAD(LAG(Level) OVER (ORDER BY (SELECT NULL))) OVER (ORDER BY (SELECT NULL))) OVER (ORDER BY (SELECT NULL))" in res_spark1

        # prev(prev(Level, 2), 1)
        kql_nest2 = "AppLogs | serialize | extend x = prev(prev(Level, 2), 1)"
        res_spark2 = translate(kql_nest2, target="spark")
        assert "LAG(LAG(Level, 2) OVER (ORDER BY (SELECT NULL)), 1) OVER (ORDER BY (SELECT NULL))" in res_spark2

    def test_inline_arithmetic_on_window_results(self):
        """Test math operations and conditional iff expressions wrapping window functions."""
        # prev(Level) + next(Level)
        kql_arith = "AppLogs | serialize | extend x = prev(Level) + next(Level)"
        res_spark = translate(kql_arith, target="spark")
        assert "LAG(Level) OVER (ORDER BY (SELECT NULL))" in res_spark
        assert "LEAD(Level) OVER (ORDER BY (SELECT NULL))" in res_spark
        assert "+" in res_spark

        # iff(prev(Level) == "Error", 1, 0)
        kql_iff = "AppLogs | serialize | extend x = iff(prev(Level) == 'Error', 1, 0)"
        res_spark_iff = translate(kql_iff, target="spark")
        assert "CASE WHEN" in res_spark_iff
        assert "LAG(Level) OVER (ORDER BY (SELECT NULL)) = 'Error'" in res_spark_iff
        assert "ELSE 0 END" in res_spark_iff

    def test_custom_string_nested_inside_window(self):
        """Verify that standard scalar functions can be cleanly nested inside window calls."""
        # prev(toupper(Level))
        kql_string = "AppLogs | serialize | extend x = prev(toupper(Level))"
        res_spark = translate(kql_string, target="spark")
        assert "LAG(UPPER(Level)) OVER (ORDER BY (SELECT NULL))" in res_spark

        # next(tolower(Level))
        kql_string2 = "AppLogs | serialize | extend x = next(tolower(Level))"
        res_tsql = translate(kql_string2, target="tsql")
        assert "LEAD(LOWER(Level)) OVER (ORDER BY (SELECT NULL))" in res_tsql


class TestSparseAndComplexSchemaHintValidation:
    """Testing dictionary configurations, none-valued, and malformed structures inside SchemaHint."""

    def test_schema_hint_as_dictionary(self):
        """Verify that dictionary configurations are robustly handled by generator."""
        hint_dict = {
            "window_spec": {
                "partition_by": ["Computer", "ServiceName"],
                "order_by": ["TimeGenerated ASC"]
            }
        }
        kql = "AppLogs | serialize | extend prev_level = prev(Level)"
        res = translate(kql, target="spark", hint=hint_dict)
        assert "LAG(Level) OVER (PARTITION BY Computer, ServiceName ORDER BY TimeGenerated ASC)" in res

    def test_sparse_values_and_malformed_lists(self):
        """Ensure malformed or sparse elements in partition/order lists are handled cleanly with zero crash."""
        hint_sparse = SchemaHint(window_spec=WindowSpec(
            partition_by=["Computer", "", None, 12345],
            order_by=[None, "TimeGenerated DESC", "", "col_xyz"]
        ))
        kql = "AppLogs | serialize | extend prev_level = prev(Level)"
        res_spark = translate(kql, target="spark", hint=hint_sparse)
        # 12345 is successfully converted to string "12345"
        assert "LAG(Level) OVER (PARTITION BY Computer, 12345 ORDER BY TimeGenerated DESC, col_xyz)" in res_spark

    def test_empty_hint_scenarios(self):
        """Ensure totally empty specs or hints degrade gracefully to unpartitioned window default."""
        kql = "AppLogs | serialize | extend prev_level = prev(Level)"
        
        # Empty window spec object
        hint_empty_spec = SchemaHint(window_spec=WindowSpec())
        res1 = translate(kql, target="spark", hint=hint_empty_spec)
        assert "LAG(Level) OVER (ORDER BY (SELECT NULL))" in res1

        # Dict empty window spec
        hint_empty_dict = {"window_spec": {}}
        res2 = translate(kql, target="spark", hint=hint_empty_dict)
        assert "LAG(Level) OVER (ORDER BY (SELECT NULL))" in res2


class TestPySparkGeneratorProjections:
    """Confirm PySpark DataFrame translations cleanly render window projections in selectExpr blocks."""

    def test_pyspark_projection_rendering(self):
        """Verify window functions inside PySpark pipelines generate clean selectExpr selections."""
        kql = "AppLogs | serialize | extend prev_level = prev(Level), next_level = next(Level)"
        hint = SchemaHint(window_spec=WindowSpec(partition_by=["Computer"], order_by=["TimeGenerated DESC"]))
        
        res = translate(kql, target="pyspark", hint=hint)
        assert "import pyspark.sql.functions as F" in res
        assert 'df = df.selectExpr("*", "LAG(Level) OVER (PARTITION BY Computer ORDER BY TimeGenerated DESC) AS prev_level", "LEAD(Level) OVER (PARTITION BY Computer ORDER BY TimeGenerated DESC) AS next_level")' in res
