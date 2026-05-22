import json
import sys
import os
from pathlib import Path

# Add src to python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from kqlbridge.parser import parse
from kqlbridge.ir import to_semantic_ir, serialize_ir
from test_validator_snapshots import SNAPSHOT_REGISTRY, SNAPSHOTS_DIR

def main():
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Regenerating snapshots inside: {SNAPSHOTS_DIR}")
    for stem, kql in SNAPSHOT_REGISTRY.items():
        print(f"Generating snapshot for: {stem}")
        try:
            ast = parse(kql)
            ir = to_semantic_ir(ast)
            serialized = serialize_ir(ir)
            
            # Ensure output is nicely formatted JSON
            target_path = SNAPSHOTS_DIR / f"{stem}.json"
            target_path.write_text(json.dumps(serialized, indent=2), encoding="utf-8")
            print(f"Saved: {target_path}")
        except Exception as e:
            print(f"Error generating snapshot for {stem}: {e}")
            raise

if __name__ == "__main__":
    main()
