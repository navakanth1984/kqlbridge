import os
import pytest
from kqlbridge import mlm_agent

@pytest.fixture(autouse=True)
def sandbox_mlm_agent(tmp_path, monkeypatch):
    """
    Autouse fixture that isolates the global mlm_agent for every single test.
    This prevents home-directory database pollution and cross-test state leaks.
    """
    temp_mem = os.path.join(tmp_path, "sandboxed_kqlbridge_memory.json")
    
    # Use monkeypatch to temporarily redirect the memory_path
    monkeypatch.setattr(mlm_agent, "memory_path", temp_mem)
    
    # Initialize/clear the sandboxed memory to guarantee clean state
    mlm_agent.clear()
    
    yield
    
    # Force reload the original memory from disk after the monkeypatched path is reverted
    mlm_agent.load_memory()
