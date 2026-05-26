from __future__ import annotations
import os
import threading
from kqlbridge.memory import TranslationMemory

def test_translation_memory_lock_thread_safety(tmp_path):
    mem_file = os.path.join(tmp_path, "thread_safe_memory.json")
    mem = TranslationMemory(memory_path=mem_file)
    
    # Run multiple threads trying to learn, recall, and register rules concurrently
    num_threads = 12
    iterations = 25
    
    threads = []
    errors = []
    
    def run_worker(thread_idx: int):
        try:
            for j in range(iterations):
                # 1. Learn standard translation success/failure
                if j % 2 == 0:
                    mem.learn(f"Query_{thread_idx}_{j}", error=f"Error_{j}")
                else:
                    mem.learn(f"Query_{thread_idx}_{j}")
                    
                # 2. Register rule
                if j % 10 == 0:
                    mem.register_rule(
                        pattern=f"Query_{thread_idx}_{j}_pattern({{col}})",
                        mapping=f"SELECT {{col}} FROM Query_{thread_idx}_{j}"
                    )
                    
                # 3. Recall
                mem.recall(f"Query_{thread_idx}_{j}")
        except Exception as e:
            errors.append(e)
            
    for i in range(num_threads):
        t = threading.Thread(target=run_worker, args=(i,))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    # Assert no errors occurred due to race conditions or lock contention
    assert not errors, f"Concurrent thread safety errors: {errors}"
    
    # Assert that all telemetries were successfully combined
    assert mem.memory["telemetry"]["total_translations"] > 0
    # Assert that save successfully persisted to file
    assert os.path.exists(mem_file)
