import os
import pytest
from kqlbridge import translate, mlm_agent, MLMAgent
from kqlbridge.mlm import MLMAgent as DirectMLMAgent

def test_mlm_telemetry_and_rules(tmp_path):
    """Verify MLM Agent handles telemetry logging, static overrides, and BML rules in isolation."""
    mem_file = os.path.join(tmp_path, "test_memory.json")
    agent = DirectMLMAgent(memory_path=mem_file)
    
    # 1. Telemetry and learn
    agent.learn("AppLogs | where X == 1", error="Syntax error: unexpected X")
    assert agent.memory["telemetry"]["total_translations"] == 1
    assert agent.memory["telemetry"]["success_count"] == 0
    failures = agent.memory["telemetry"]["failures"]
    assert "AppLogs | where X == 1" in failures
    assert failures["AppLogs | where X == 1"]["count"] == 1
    assert failures["AppLogs | where X == 1"]["error"] == "Syntax error: unexpected X"
    
    # 2. Static override
    agent.learn("AppLogs | unsupported_op", fix_sql="SELECT * FROM AppLogs -- overridden")
    assert agent.recall("AppLogs | unsupported_op") == "SELECT * FROM AppLogs -- overridden"
    
    # 3. Bridge Meta-Language (BML) rules
    agent.register_rule(
        pattern="AppLogs | custom_op({col}, {val})",
        mapping="SELECT * FROM AppLogs WHERE {col} = {val}"
    )
    
    # Test matching and dynamic binding
    res = agent.recall("AppLogs | custom_op(Message, 'hello')")
    assert res == "SELECT * FROM AppLogs WHERE Message = 'hello'"
    
    # Space variations
    res_spaced = agent.recall("AppLogs   |   custom_op(  Message  ,   'hello'  )")
    assert res_spaced == "SELECT * FROM AppLogs WHERE Message = 'hello'"
    
    # 4. Clear
    agent.clear()
    assert agent.recall("AppLogs | unsupported_op") is None
    assert agent.memory["telemetry"]["total_translations"] == 0


def test_global_translate_integration():
    """Verify translate() uses the global mlm_agent for recall, logging, and correction."""
    kql_invalid = "AppLogs | this_op_will_crash_the_parser_totally"
    
    # 1. Verify invalid KQL raises standard transpiler error and logs telemetry
    with pytest.raises(ValueError) as excinfo:
        translate(kql_invalid)
    
    assert "Unsupported KQL syntax" in str(excinfo.value)
    assert kql_invalid in mlm_agent.memory["telemetry"]["failures"]
    assert mlm_agent.memory["telemetry"]["failures"][kql_invalid]["count"] == 1
    
    # 2. Register static override for the invalid KQL and confirm translate() intercepts and bypasses
    mlm_agent.learn(kql_invalid, fix_sql="SELECT * FROM AppLogs WHERE Intercepted = true")
    
    intercepted_sql = translate(kql_invalid)
    assert intercepted_sql == "SELECT * FROM AppLogs WHERE Intercepted = true"
    assert mlm_agent.memory["telemetry"]["success_count"] == 1
    
    # 3. Register a BML rule on the global agent and verify transparent translation
    mlm_agent.register_rule(
        pattern="AppLogs | process_tag({tag})",
        mapping="SELECT * FROM AppLogs WHERE Tags LIKE '%{tag}%'"
    )
    
    res = translate("AppLogs | process_tag(critical_bug)")
    assert res == "SELECT * FROM AppLogs WHERE Tags LIKE '%critical_bug%'"
