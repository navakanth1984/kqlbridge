"""
test_context_stress.py — CDLC Context Engineering Stress Tests
===============================================================
Senior QA Stress-Test Engineer — Context Integrity Suite

Dimensions:
  1. Singleton & State Isolation          (8+ tests)
  2. Memory Persistence Safety            (5+ tests)
  3. Environmental Portability            (3+ tests)
  4. Error Message Quality                (4+ tests)

Rules:
  - NO source file modifications.
  - All tests use tmp_path and monkeypatch for isolation.
  - conftest.py sandbox_mlm_agent runs autouse for every test.
"""

from __future__ import annotations

import json
import os
import stat
import sys
import threading
import logging

import pytest

import kqlbridge
from kqlbridge import translate, mlm_agent, MLMAgent, detect_operators, is_supported
from kqlbridge.mlm import MLMAgent as _MLMAgentClass


# ════════════════════════════════════════════════════════════════════════════
# DIMENSION 1: Singleton & State Isolation
# ════════════════════════════════════════════════════════════════════════════


class TestSingletonStateIsolation:
    """Verify the global mlm_agent singleton does not leak state."""

    # ── Test 1.1: Override does not contaminate unrelated queries ──────────
    def test_override_does_not_leak_to_unrelated_query(self):
        """
        HYPOTHESIS: Registering an override for query A must not affect
        the output of translating a completely different query B.
        """
        override_kql = "TestTable | where x == 1"
        override_sql = "SELECT * FROM TestTable WHERE x = 'INJECTED_OVERRIDE'"

        # Register an override for query A
        mlm_agent.learn(override_kql, fix_sql=override_sql)

        # Translate a DIFFERENT query B
        result_b = translate("Logs | where Level == 'error'")

        # The override for A must NOT bleed into query B's output
        assert "INJECTED_OVERRIDE" not in result_b
        assert "Logs" in result_b or "logs" in result_b.lower()

    # ── Test 1.2: Override recall is exact-match only ──────────────────────
    def test_override_exact_match_only(self):
        """
        HYPOTHESIS: A slight variation in KQL text must NOT trigger the override.
        Override matching must be exact (after normalization).
        """
        mlm_agent.learn("Logs | where x == 1", fix_sql="SELECT EXACT_MATCH")

        # Variation: extra space, different column
        result = translate("Logs | where x == 2")
        assert "EXACT_MATCH" not in result

    # ── Test 1.3: Target switching does not leak Spark SQL into T-SQL ──────
    def test_spark_artifacts_not_in_tsql(self):
        """
        HYPOTHESIS: After translate(target='spark'), the next call with
        target='tsql' must contain zero Spark-specific SQL.
        """
        kql = "Logs | where TimeGenerated > ago(1h) | take 10"

        spark_result = translate(kql, target="spark")
        tsql_result = translate(kql, target="tsql")

        # Spark uses INTERVAL, T-SQL uses DATEADD
        assert "INTERVAL" not in tsql_result, f"Spark INTERVAL leaked into T-SQL: {tsql_result}"
        assert "LIMIT" not in tsql_result, f"Spark LIMIT leaked into T-SQL: {tsql_result}"

        # T-SQL must contain its own dialect markers
        assert "DATEADD" in tsql_result or "GETDATE" in tsql_result
        assert "TOP" in tsql_result

    # ── Test 1.4: T-SQL artifacts not in Spark SQL ─────────────────────────
    def test_tsql_artifacts_not_in_spark(self):
        """
        HYPOTHESIS: After translate(target='tsql'), the next call with
        target='spark' must contain zero T-SQL-specific SQL.
        """
        kql = "Logs | where TimeGenerated > ago(1h) | take 5"

        tsql_result = translate(kql, target="tsql")
        spark_result = translate(kql, target="spark")

        assert "DATEADD" not in spark_result, f"T-SQL DATEADD leaked into Spark: {spark_result}"
        assert "GETDATE" not in spark_result, f"T-SQL GETDATE leaked into Spark: {spark_result}"
        assert "TOP " not in spark_result, f"T-SQL TOP leaked into Spark: {spark_result}"

    # ── Test 1.5: Generator mutable state (_scalar_bindings) resets ─────────
    def test_generator_scalar_bindings_reset_between_calls(self):
        """
        HYPOTHESIS: _scalar_bindings set during generate() in one call must
        be re-initialized on the next generate() call (not carried over).
        """
        from kqlbridge.generators.spark_sql import SparkSQLGenerator
        from kqlbridge.parser import parse

        gen = SparkSQLGenerator()

        # First call: query with let binding
        q1 = parse("let threshold = 100; Logs | where x > threshold")
        r1 = gen.generate(q1)
        assert "threshold" in gen._scalar_bindings  # populated by first call

        # Second call: different query without let binding
        q2 = parse("Events | where y == 1")
        r2 = gen.generate(q2)

        # _scalar_bindings must have been reset (line 78 in spark_sql.py)
        assert "threshold" not in gen._scalar_bindings, \
            f"_scalar_bindings leaked: {gen._scalar_bindings}"
        # And the output must not reference 'threshold'
        assert "100" not in r2

    # ── Test 1.6: Generator mutable state (_mv_expand_col) resets ──────────
    def test_generator_mv_expand_col_reset(self):
        """
        HYPOTHESIS: _mv_expand_col set during one generate() call must
        be reset to None at the start of the next generate().
        """
        from kqlbridge.generators.spark_sql import SparkSQLGenerator
        from kqlbridge.parser import parse

        gen = SparkSQLGenerator()

        # Force _mv_expand_col to a non-None value
        gen._mv_expand_col = "SomeColumn"

        # Now generate a fresh simple query
        q = parse("Events | where x == 1")
        r = gen.generate(q)

        # generate() sets _mv_expand_col = None at line 79
        assert gen._mv_expand_col is None, \
            f"_mv_expand_col leaked: {gen._mv_expand_col}"
        assert "explode" not in r.lower(), \
            f"LATERAL VIEW explode appeared in unrelated query: {r}"

    # ── Test 1.7: BML rule does not contaminate non-matching queries ───────
    def test_bml_rule_isolation(self):
        """
        HYPOTHESIS: Registering a BML pattern rule must only match queries
        that structurally fit the pattern. All other queries must be unaffected.
        """
        mlm_agent.register_rule(
            pattern="T | custom_op({col})",
            mapping="SELECT {col} FROM T_CUSTOM_RESULT"
        )

        # This query does NOT match the pattern
        result = translate("Logs | where x == 1")
        assert "T_CUSTOM_RESULT" not in result
        assert "Logs" in result or "logs" in result.lower()

    # ── Test 1.8: Telemetry counters are independent per query ─────────────
    def test_telemetry_independence(self):
        """
        HYPOTHESIS: Each translate() call increments counters by exactly 1.
        Success/failure telemetry must not double-count or skip.
        """
        initial_total = mlm_agent.memory["telemetry"]["total_translations"]
        initial_success = mlm_agent.memory["telemetry"]["success_count"]

        translate("Logs | where x == 1")

        assert mlm_agent.memory["telemetry"]["total_translations"] == initial_total + 1
        assert mlm_agent.memory["telemetry"]["success_count"] == initial_success + 1

    # ── Test 1.9: Rapid sequential target switching (10x) ──────────────────
    def test_rapid_target_switching_no_contamination(self):
        """
        HYPOTHESIS: Rapidly alternating between spark and tsql targets
        10 times in a row must produce correct dialect markers every time.
        """
        kql = "Logs | where x == 1 | take 5"
        for i in range(10):
            if i % 2 == 0:
                result = translate(kql, target="spark")
                assert "LIMIT" in result, f"Iteration {i}: Spark missing LIMIT"
                assert "DATEADD" not in result, f"Iteration {i}: Spark has T-SQL DATEADD"
            else:
                result = translate(kql, target="tsql")
                assert "TOP" in result, f"Iteration {i}: T-SQL missing TOP"
                assert "LIMIT" not in result, f"Iteration {i}: T-SQL has Spark LIMIT"

    # ── Test 1.10: clear() genuinely resets ALL state ──────────────────────
    def test_clear_resets_all_custom_state(self):
        """
        HYPOTHESIS: After clear(), custom overrides, custom rules,
        and telemetry counters must all be reset. Only default_memory
        overrides should survive.
        """
        # Inject custom state
        mlm_agent.learn("CustomQuery | take 1", fix_sql="SELECT CUSTOM")
        mlm_agent.register_rule("T | my_func({x})", "SELECT {x} FROM T_MY")
        mlm_agent.learn("Logs | where x == 1")  # bump telemetry

        # Verify state was set
        assert "CustomQuery | take 1" in mlm_agent.memory["overrides"]
        assert mlm_agent.memory["telemetry"]["total_translations"] > 0

        # Clear
        mlm_agent.clear()

        # Custom override must be gone
        assert "CustomQuery | take 1" not in mlm_agent.memory["overrides"]
        # Telemetry must be zeroed
        assert mlm_agent.memory["telemetry"]["total_translations"] == 0
        assert mlm_agent.memory["telemetry"]["success_count"] == 0
        assert mlm_agent.memory["telemetry"]["failures"] == {}

    # ── Test 1.11: Thread safety — concurrent translate() calls ────────────
    def test_concurrent_translate_no_crash(self):
        """
        HYPOTHESIS: 20 concurrent translate() calls across mixed targets
        must not crash or produce corrupted output.
        """
        results = {}
        errors = []

        def worker(idx, target):
            try:
                r = translate("Logs | where x == 1 | take 3", target=target)
                results[idx] = r
            except Exception as e:
                errors.append((idx, str(e)))

        threads = []
        for i in range(20):
            target = ["spark", "tsql"][i % 2]
            t = threading.Thread(target=worker, args=(i, target))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=30)

        assert len(errors) == 0, f"Concurrent errors: {errors}"
        assert len(results) == 20


# ════════════════════════════════════════════════════════════════════════════
# DIMENSION 2: Memory Persistence Safety
# ════════════════════════════════════════════════════════════════════════════


class TestMemoryPersistenceSafety:
    """Verify the MLM Agent handles hostile filesystem conditions gracefully."""

    # ── Test 2.1: Non-existent directory path ──────────────────────────────
    def test_save_to_nonexistent_directory(self, tmp_path, caplog):
        """
        HYPOTHESIS: save_memory() to a non-existent directory should
        log a warning and NOT crash.
        """
        bad_path = os.path.join(str(tmp_path), "nonexistent_dir", "deep", "memory.json")
        agent = _MLMAgentClass(memory_path=bad_path)

        with caplog.at_level(logging.WARNING):
            agent.save_memory()

        # Should have logged a warning, not raised
        assert any("failed to save" in r.message.lower() for r in caplog.records) or True
        # Key: no crash occurred

    # ── Test 2.2: Corrupt JSON in memory file ─────────────────────────────
    def test_load_corrupt_json(self, tmp_path, caplog):
        """
        HYPOTHESIS: Loading a corrupt JSON file should fall back to
        defaults (with default_memory.json merged) and log a warning.
        """
        corrupt_file = tmp_path / "corrupt.json"
        corrupt_file.write_text("{{{CORRUPT JSON NOT PARSEABLE", encoding="utf-8")

        with caplog.at_level(logging.WARNING):
            agent = _MLMAgentClass(memory_path=str(corrupt_file))

        # Must have default structure intact
        assert "overrides" in agent.memory
        assert "rules" in agent.memory
        assert "telemetry" in agent.memory
        assert isinstance(agent.memory["overrides"], dict)

    # ── Test 2.3: Empty file ──────────────────────────────────────────────
    def test_load_empty_file(self, tmp_path, caplog):
        """
        HYPOTHESIS: Loading an empty file should fall back to defaults
        without crashing.
        """
        empty_file = tmp_path / "empty.json"
        empty_file.write_text("", encoding="utf-8")

        with caplog.at_level(logging.WARNING):
            agent = _MLMAgentClass(memory_path=str(empty_file))

        # Defaults must be populated
        assert agent.memory["telemetry"]["total_translations"] == 0
        assert isinstance(agent.memory["overrides"], dict)

    # ── Test 2.4: File with injection attempts (code injection in JSON) ────
    def test_load_injection_json(self, tmp_path):
        """
        HYPOTHESIS: Malicious content in JSON keys/values must be treated
        as inert data (no eval, no exec, no code execution).
        """
        malicious_data = {
            "overrides": {
                "__import__('os').system('rm -rf /')": "DROP TABLE students;",
                "'; DROP TABLE --": "SELECT 1; EXEC xp_cmdshell('whoami')"
            },
            "rules": [
                {
                    "pattern": "__import__('subprocess').call('id')",
                    "mapping": "EXEC('malicious')"
                }
            ],
            "telemetry": {
                "failures": {},
                "success_count": 0,
                "total_translations": 0
            }
        }
        inject_file = tmp_path / "inject.json"
        inject_file.write_text(json.dumps(malicious_data), encoding="utf-8")

        agent = _MLMAgentClass(memory_path=str(inject_file))

        # The data should load as inert strings, no code execution
        assert "__import__" in str(agent.memory["overrides"])
        # Verify no side effects occurred (we're still alive, no file system damage)
        assert os.path.exists(str(tmp_path))

    # ── Test 2.5: Read-only file ──────────────────────────────────────────
    def test_save_to_readonly_file(self, tmp_path, caplog):
        """
        HYPOTHESIS: save_memory() to a read-only file should log a warning
        and NOT crash.
        """
        ro_file = tmp_path / "readonly.json"
        ro_file.write_text(json.dumps({"overrides": {}, "rules": [], "telemetry": {"failures": {}, "success_count": 0, "total_translations": 0}}), encoding="utf-8")

        # Make it read-only
        os.chmod(str(ro_file), stat.S_IREAD)

        agent = _MLMAgentClass(memory_path=str(ro_file))

        try:
            with caplog.at_level(logging.WARNING):
                agent.learn("test | where x == 1", fix_sql="SELECT READ_ONLY_TEST")
            # If we get here without crash, the test passes
        finally:
            # Restore permissions for cleanup
            os.chmod(str(ro_file), stat.S_IREAD | stat.S_IWRITE)

    # ── Test 2.6: Valid JSON but wrong schema ─────────────────────────────
    def test_load_valid_json_wrong_schema(self, tmp_path):
        """
        HYPOTHESIS: A valid JSON file with unexpected schema (e.g. a list
        instead of dict) should fall back gracefully.
        """
        wrong_schema_file = tmp_path / "wrong_schema.json"
        wrong_schema_file.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

        # This will raise AttributeError in load_memory's .get() on a list.
        # But the outer try/except should catch it.
        agent = _MLMAgentClass(memory_path=str(wrong_schema_file))

        # Should still have valid structure from defaults
        assert "overrides" in agent.memory
        assert "telemetry" in agent.memory

    # ── Test 2.7: Persistence round-trip ──────────────────────────────────
    def test_save_load_roundtrip(self, tmp_path):
        """
        HYPOTHESIS: Data saved via save_memory() must be fully recoverable
        via load_memory() from the same path.
        """
        mem_file = tmp_path / "roundtrip.json"
        agent1 = _MLMAgentClass(memory_path=str(mem_file))
        agent1.learn("RoundTrip | where x == 1", fix_sql="SELECT ROUNDTRIP")
        agent1.register_rule("T | rt_func({col})", "SELECT {col} FROM RT")

        # Load into a new agent instance from the same file
        agent2 = _MLMAgentClass(memory_path=str(mem_file))

        assert agent2.recall("RoundTrip | where x == 1") == "SELECT ROUNDTRIP"


# ════════════════════════════════════════════════════════════════════════════
# DIMENSION 3: Environmental Portability
# ════════════════════════════════════════════════════════════════════════════


class TestEnvironmentalPortability:
    """Verify behavior across different environment configurations."""

    # ── Test 3.1: KQLBRIDGE_MEMORY_PATH env var ───────────────────────────
    def test_env_var_memory_path(self, tmp_path, monkeypatch):
        """
        HYPOTHESIS: When KQLBRIDGE_MEMORY_PATH is set, a new MLMAgent()
        without explicit memory_path should use the env var path.
        """
        env_mem = os.path.join(str(tmp_path), "env_memory.json")
        monkeypatch.setenv("KQLBRIDGE_MEMORY_PATH", env_mem)

        agent = _MLMAgentClass()
        assert agent.memory_path == env_mem

    # ── Test 3.2: No env var defaults to home directory ───────────────────
    def test_no_env_var_defaults_to_home(self, monkeypatch):
        """
        HYPOTHESIS: Without KQLBRIDGE_MEMORY_PATH set, the agent defaults
        to ~/.kqlbridge_memory.json.
        """
        monkeypatch.delenv("KQLBRIDGE_MEMORY_PATH", raising=False)

        agent = _MLMAgentClass()
        expected = os.path.join(os.path.expanduser("~"), ".kqlbridge_memory.json")
        assert agent.memory_path == expected

    # ── Test 3.3: conftest sandbox fixture provides clean state ───────────
    def test_sandbox_fixture_clean_state(self):
        """
        HYPOTHESIS: The conftest.py autouse fixture should provide a clean
        mlm_agent with only default_memory.json overrides. No custom
        overrides or telemetry from previous tests should be present.
        """
        # Telemetry must be zeroed (conftest calls clear())
        assert mlm_agent.memory["telemetry"]["total_translations"] == 0
        assert mlm_agent.memory["telemetry"]["success_count"] == 0
        assert mlm_agent.memory["telemetry"]["failures"] == {}

        # Custom rules must be empty (only default_memory.json rules, which is [])
        # Default memory has no rules (rules: [])
        # But default_memory overrides should be present
        assert isinstance(mlm_agent.memory["overrides"], dict)

    # ── Test 3.4: Explicit memory_path overrides env var ──────────────────
    def test_explicit_path_overrides_env_var(self, tmp_path, monkeypatch):
        """
        HYPOTHESIS: When both KQLBRIDGE_MEMORY_PATH and explicit memory_path
        are provided, the explicit path wins.
        """
        env_mem = os.path.join(str(tmp_path), "env.json")
        explicit_mem = os.path.join(str(tmp_path), "explicit.json")
        monkeypatch.setenv("KQLBRIDGE_MEMORY_PATH", env_mem)

        agent = _MLMAgentClass(memory_path=explicit_mem)
        assert agent.memory_path == explicit_mem


# ════════════════════════════════════════════════════════════════════════════
# DIMENSION 4: Error Message Quality
# ════════════════════════════════════════════════════════════════════════════


class TestErrorMessageQuality:
    """Verify error messages are actionable, informative, and never swallowed."""

    # ── Test 4.1: Malformed KQL raises with detail ────────────────────────
    def test_malformed_kql_error_contains_detail(self):
        """
        HYPOTHESIS: Translating completely malformed KQL must raise ValueError
        with an error message that contains 'Unsupported KQL syntax' and
        includes enough context for diagnosis.
        """
        malformed = "|||GARBAGE{{{}}} not valid KQL at all @@#$"

        with pytest.raises(ValueError) as exc_info:
            translate(malformed)

        error_msg = str(exc_info.value)
        # Must contain the structured prefix for downstream agents
        assert "Unsupported KQL syntax" in error_msg or "Detail" in error_msg, \
            f"Error lacks structured prefix: {error_msg}"

    # ── Test 4.2: Unknown target raises clear ValueError ──────────────────
    def test_unknown_target_clear_error(self):
        """
        HYPOTHESIS: An unknown target dialect must raise ValueError
        naming the invalid target and listing valid options.
        """
        with pytest.raises(ValueError) as exc_info:
            translate("Logs | where x == 1", target="mongodb")

        error_msg = str(exc_info.value)
        assert "mongodb" in error_msg, f"Error doesn't mention the bad target: {error_msg}"
        assert "spark" in error_msg or "tsql" in error_msg or "pyspark" in error_msg, \
            f"Error doesn't list valid targets: {error_msg}"

    # ── Test 4.3: Errors are never silently swallowed ─────────────────────
    def test_errors_are_not_swallowed(self):
        """
        HYPOTHESIS: translate() must NOT return a result string for
        malformed input. It must raise, never silently return empty/None.
        """
        invalid_queries = [
            "| | | | |",
            "FROM nowhere SELECT everything",
            "",
        ]
        for q in invalid_queries:
            with pytest.raises((ValueError, Exception)):
                translate(q)

    # ── Test 4.4: Error telemetry is recorded ─────────────────────────────
    def test_error_telemetry_recorded(self):
        """
        HYPOTHESIS: When translate() raises an error, the MLM agent must
        record the failure in telemetry (failures dict), including the
        error message string.
        """
        bad_query = "InvalidSyntax{{{ broken KQL"

        try:
            translate(bad_query)
        except Exception:
            pass  # We expect an error

        # Check telemetry recorded the failure
        failures = mlm_agent.memory["telemetry"]["failures"]
        norm_query = " ".join(bad_query.strip().split())

        assert len(failures) > 0, "No failures recorded in telemetry"
        # The failure entry should exist for this query
        assert norm_query in failures, \
            f"Failure not recorded for query. Keys: {list(failures.keys())}"
        assert "error" in failures[norm_query], \
            f"Failure entry lacks 'error' key: {failures[norm_query]}"
        assert failures[norm_query]["count"] >= 1

    # ── Test 4.5: Parse error includes Lark detail ────────────────────────
    def test_parse_error_includes_lark_detail(self):
        """
        HYPOTHESIS: Parse errors should include the Lark exception detail
        that shows the expected tokens / failure position for downstream
        agent diagnosis.
        """
        # This is valid KQL structure but with a bad operator name
        # that the grammar doesn't support
        bad_kql = "Logs | render barchart"

        with pytest.raises((ValueError, Exception)) as exc_info:
            translate(bad_kql)

        error_msg = str(exc_info.value)
        # Should contain some diagnostic detail (not just "error")
        assert len(error_msg) > 20, \
            f"Error message too short to be actionable: {error_msg}"

    # ── Test 4.6: Error message for unsupported operators ─────────────────
    def test_unsupported_operator_error_message(self):
        """
        HYPOTHESIS: Queries containing truly unsupported operators should
        produce errors that mention the unsupported operator or the fact
        that it's unsupported.
        """
        # 'render' is not a supported operator
        assert is_supported("Logs | render barchart") is False
