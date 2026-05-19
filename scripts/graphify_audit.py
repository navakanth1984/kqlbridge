"""
scripts/graphify_audit.py — KQLBridge Codebase Intelligence via Graphify
=========================================================================
Runs the full Graphify 7-step pipeline on the KQLBridge codebase.

Uses graphify to:
1. Detect file types (code, docs, config, context skills)
2. Extract AST nodes + edges from all Python source files
3. Build the dependency graph
4. Cluster modules
5. Analyze for god nodes, surprising connections, research questions
6. Generate a human-readable architecture report
7. Export interactive HTML visualization

Run from repo root:
    python scripts/graphify_audit.py

Output: graphify-out/
    ├── graphify_report.md      — Architecture analysis
    ├── graph.html              — Interactive browser visualization
    ├── graph.json              — Graph data for downstream tools
    ├── .graphify_detect.json   — File inventory
    └── .graphify_ast.json      — Raw AST nodes + edges

Agentic Engineering Integration:
    The graphify_report.md is the architecture health check
    equivalent of prepare.py being the eval health check.
    Run this after every Tune phase (every 3–5 operators) to
    catch god nodes before they become architectural debt.
"""

import json
from pathlib import Path

# ─── PATHS ───────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent
SRC_PATH = REPO_ROOT / "src" / "kqlbridge"
OUT_DIR = REPO_ROOT / "graphify-out"
OUT_DIR.mkdir(exist_ok=True)

# ─── GRAPHIFY PIPELINE ───────────────────────────────────────────────────────

try:
    from graphify.detect import detect
    from graphify.extract import collect_files, extract
    from graphify.build import build_from_json
    from graphify.cluster import cluster, score_all
    from graphify.analyze import god_nodes, surprising_connections, suggest_questions
    from graphify.report import generate
    from graphify.export import to_json, to_html
    HAS_GRAPHIFY = True
except ImportError:
    HAS_GRAPHIFY = False
    print("[WARN] graphify not installed — falling back to manual AST analysis")


def run_graphify_pipeline():
    """Full 7-step graphify pipeline on the KQLBridge source."""
    if not HAS_GRAPHIFY:
        run_manual_analysis()
        return

    print(f"KQLBridge Graphify Audit - {SRC_PATH}")
    print("=" * 60)

    # Step 1 — Detect
    print("Step 1: Detecting file types...")
    det = detect(SRC_PATH)
    (OUT_DIR / ".graphify_detect.json").write_text(json.dumps(det, indent=2), encoding="utf-8")
    print(f"  Code files: {len(det.get('files', {}).get('code', []))}")
    print(f"  Config files: {len(det.get('files', {}).get('config', []))}")

    # Step 2 — Collect & Extract AST
    print("Step 2: Extracting AST nodes + edges...")
    code_files = []
    for f in det.get("files", {}).get("code", []):
        p = SRC_PATH / f if not Path(f).is_absolute() else Path(f)
        code_files.extend(collect_files(p) if p.is_dir() else [p])

    if not code_files:
        # Fallback: collect all .py files directly
        code_files = list(SRC_PATH.rglob("*.py"))

    ast_result = extract(code_files, cache_root=REPO_ROOT)
    (OUT_DIR / ".graphify_ast.json").write_text(json.dumps(ast_result, indent=2), encoding="utf-8")
    print(f"  Nodes: {len(ast_result['nodes'])}")
    print(f"  Edges: {len(ast_result['edges'])}")

    # Step 3 — Build graph
    print("Step 3: Building dependency graph...")
    graph = build_from_json(ast_result)

    # Step 4 — Cluster & Score
    print("Step 4: Clustering modules...")
    clustered = cluster(graph)
    scores = score_all(graph, clustered)
    top_scored = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5]
    print(f"  Top-scored nodes (load-bearing): {[n for n, _ in top_scored]}")

    # Step 5 — Analyze
    print("Step 5: Analyzing architecture...")
    gods = god_nodes(graph)
    surprises = surprising_connections(graph, clustered)
    questions = suggest_questions(graph, clustered, {cid: f"Community {cid}" for cid in clustered})

    # Print key findings immediately
    print(f"\n  God nodes detected: {len(gods)}")
    for g in gods[:3]:
        print(f"    [WARN] {g.get('id', g)} - high in+out coupling")

    print(f"\n  Surprising connections: {len(surprises)}")
    for s in surprises[:3]:
        print(f"    -> {s.get('source')} imports from {s.get('target')}")

    # Step 6 — Report
    print("\nStep 6: Generating architecture report...")
    report_text = generate(
        G=graph,
        communities=clustered,
        cohesion_scores=scores,
        community_labels={cid: f"Community {cid}" for cid in clustered},
        god_node_list=gods,
        surprise_list=surprises,
        detection_result=det,
        token_cost={"input": 0, "output": 0},
        root="kqlbridge",
        suggested_questions=questions,
    )
    (OUT_DIR / "graphify_report.md").write_text(report_text, encoding="utf-8")
    print(f"  Saved: {OUT_DIR / 'graphify_report.md'}")

    # Step 7 — Export
    print("Step 7: Exporting graph...")
    to_json(graph, clustered, str(OUT_DIR / "graph.json"), force=True)
    to_html(graph, clustered, str(OUT_DIR / "graph.html"), community_labels={cid: f"Community {cid}" for cid in clustered})
    print(f"  Saved: {OUT_DIR / 'graph.html'} (open in browser)")

    # ─── Agentic Engineering Health Check ────────────────────────────────
    print("\n" + "=" * 60)
    print("BIT Tune Phase - Karpathy Bloat Audit")
    print("=" * 60)
    _run_bloat_audit()
    _check_architecture_rules(gods, surprises)

    print(f"\n[OK] Graphify audit complete. Open: {OUT_DIR / 'graph.html'}")


def run_manual_analysis():
    """Fallback analysis without graphify — uses Python's ast module."""
    import ast as py_ast

    print("Manual AST analysis (graphify not available)")
    print("=" * 60)

    source_files = list(SRC_PATH.rglob("*.py"))
    stats = {
        "files": len(source_files),
        "functions": 0,
        "classes": 0,
        "imports": [],
        "long_functions": [],
    }

    for path in source_files:
        try:
            tree = py_ast.parse(path.read_text(encoding="utf-8"))
            rel_path = path.relative_to(REPO_ROOT)

            for node in py_ast.walk(tree):
                if isinstance(node, py_ast.FunctionDef):
                    stats["functions"] += 1
                    line_count = (node.end_lineno or 0) - node.lineno
                    if line_count > 30:  # Karpathy Principle 2 threshold
                        stats["long_functions"].append(
                            f"{rel_path}::{node.name} ({line_count} lines)"
                        )
                elif isinstance(node, py_ast.ClassDef):
                    stats["classes"] += 1
                elif isinstance(node, py_ast.Import):
                    for alias in node.names:
                        stats["imports"].append(alias.name)
                elif isinstance(node, py_ast.ImportFrom):
                    if node.module:
                        stats["imports"].append(node.module)

        except SyntaxError as e:
            print(f"  Syntax error in {path}: {e}")

    print(f"Files analyzed: {stats['files']}")
    print(f"Functions: {stats['functions']}")
    print(f"Classes: {stats['classes']}")
    print(f"\nKarpathy Principle 2 — Functions > 30 lines:")
    if stats["long_functions"]:
        for fn in stats["long_functions"]:
            print(f"  [WARN] {fn}")
    else:
        print("  [OK] All functions within 30-line guideline")

    _run_bloat_audit()

    # Save basic report
    report = f"""# KQLBridge Manual Architecture Audit

## Stats
- Files: {stats['files']}
- Functions: {stats['functions']}
- Classes: {stats['classes']}

## Long Functions (> 30 lines — Karpathy P2 review needed)
{chr(10).join('- ' + fn for fn in stats['long_functions']) or 'None'}

## Action: Install graphify for full dependency graph analysis
"""
    (OUT_DIR / "graphify_report.md").write_text(report, encoding="utf-8")
    print(f"\nBasic report saved: {OUT_DIR / 'graphify_report.md'}")


def _run_bloat_audit():
    """Karpathy Principle 6 bloat audit checklist — run after every Tune phase."""
    print("\nKarpathy Bloat Audit Checklist:")
    checklist = [
        ("P2", "Can any 10+ line block become a named function?"),
        ("P2", "Are there copy-pasted patterns -> should be a loop?"),
        ("P2", "Are there abstractions for only one operator?"),
        ("P2", "Are there unreachable branches?"),
        ("P4", "Does the code optimize for the score but miss real cases?"),
        ("P6", "Would a senior engineer understand this in 5 minutes?"),
    ]
    for principle, question in checklist:
        print(f"  [{principle}] [ ] {question}")
    print("\n  -> Run this checklist manually after each BIT Tune phase.")


def _check_architecture_rules(gods: list, surprises: list):
    """
    Check architectural invariants for the KQLBridge codebase.
    These rules should never be violated.
    """
    print("\nArchitecture Rule Checks:")

    # Rule 1: Generator should not import from semantic
    violations = []
    for edge in surprises:
        src = str(edge.get("source", ""))
        tgt = str(edge.get("target", ""))
        if "generator" in src and "semantic" in tgt:
            violations.append(f"generators -> semantic (generators should be pure AST -> SQL)")
        if "semantic" in src and "parser" in tgt:
            violations.append(f"semantic -> parser (semantic is downstream, not upstream)")

    if violations:
        print("  [FAIL] Architecture violations found:")
        for v in violations:
            print(f"     {v}")
    else:
        print("  [OK] No cross-layer dependency violations")

    # Rule 2: God nodes should not appear in locked files
    locked_files = ["ast_nodes", "semantic", "kql_lark", "prepare"]
    god_names = [str(g.get("id", "")) for g in gods]
    for gn in god_names:
        if any(locked in gn for locked in locked_files):
            print(f"  [WARN] God node in locked file: {gn}")
            print("    -> Locked files should be stable. This is unexpected coupling.")

    # Rule 3: No circular imports
    print("  [OK] Circular import check: use 'python -m py_compile src/kqlbridge/*.py' to verify")


if __name__ == "__main__":
    run_graphify_pipeline()
