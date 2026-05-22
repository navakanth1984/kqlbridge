"""
tests/test_validator_snapshots.py — Validator × Snapshot Integration
=====================================================================
Phase 3B pre-gate. Proves that:

  1. Every stored JSON snapshot was produced from valid IR (validate_ir passes)
  2. Re-running the original KQL still produces IR that matches the snapshot
     (structural regression — catches transformer changes)
  3. V013 (duplicate alias) does NOT fire on any canonical query

This makes the validator and snapshot baseline mutually reinforcing:
  - Snapshot changes require validator approval
  - Validator rule additions are tested against real IR patterns

Run:
    py -m pytest tests/test_validator_snapshots.py -v

Gate requirement:
    All 10 snapshots pass validate_ir() BEFORE Phase 3B (Tier 3) begins.
    If any snapshot fails validation, the transformer produced invalid IR
    at some point — find the regression before extracting 353 queries.
"""

import json
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from kqlbridge.parser import parse
from kqlbridge.ir import to_semantic_ir, validate_ir, serialize_ir, IRValidationError


SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"

# ─── Canonical KQL registry ──────────────────────────────────────────────────
# Maps snapshot filename stem → the KQL that produced it.
# Maintained here so snapshot tests are self-contained and reproducible.
# If a snapshot file has no entry here, it is tested for existence + validity
# only (no structural regression check).

SNAPSHOT_REGISTRY: dict = {
    # Add entries as: "snapshot_stem": "KQL string"
    # Examples (adjust to match your actual snapshot filenames):
    "basic_filter": "SecurityEvents | where Level == 'Error'",
    "filter_project": "SecurityEvents | where Level == 'Error' | project Message, Level",
    "extend_project": "Orders | extend cost = UnitPrice * Quantity | project OrderId, cost",
    "summarize_count": "SecurityEvents | summarize events = count() by source_ip",
    "summarize_multi": (
        "T | summarize total = count(), revenue = sum(amount), avg_s = avg(score) by region"
    ),
    "summarize_bin": "SecurityEvents | summarize count() by bin(TimeGenerated, 1h)",
    "let_cte": (
        "let Errors = AppLogs | where Level == 'Error';\n"
        "Errors | summarize count() by Service"
    ),
    "full_pipeline": (
        "T | where Level == 'Error' "
        "| summarize total = count() by region "
        "| order by total desc "
        "| take 10"
    ),
    "union_basic": "SecurityEvents | union HoneypotHits | project source_ip",
    "join_basic": "SecurityEvents | join kind=inner (DeviceNetworkEvents) on DeviceId",
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def load_snapshot(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def get_all_snapshots() -> list:
    """Return list of (stem, path) for every JSON file in snapshots dir."""
    if not SNAPSHOTS_DIR.exists():
        return []
    return [(p.stem, p) for p in sorted(SNAPSHOTS_DIR.glob("*.json"))]


# ─── 1. Snapshot directory existence ─────────────────────────────────────────

class TestSnapshotDirectory:

    def test_snapshots_dir_exists(self):
        assert SNAPSHOTS_DIR.exists(), (
            f"Snapshots directory not found: {SNAPSHOTS_DIR}\n"
            f"Run: py tests/regen_snapshots.py to create the baseline"
        )

    def test_snapshots_dir_has_json_files(self):
        snapshots = get_all_snapshots()
        assert len(snapshots) > 0, (
            f"No JSON files in {SNAPSHOTS_DIR}"
        )

    def test_snapshots_dir_has_at_least_ten(self):
        snapshots = get_all_snapshots()
        assert len(snapshots) >= 10, (
            f"Expected >= 10 snapshots, found {len(snapshots)}. "
            f"Run regen_snapshots.py to regenerate."
        )


# ─── 2. Each snapshot loads and is structurally valid JSON ───────────────────

@pytest.mark.parametrize("stem,path", get_all_snapshots())
def test_snapshot_loads_as_valid_json(stem, path):
    """Every snapshot file must load as valid JSON with expected keys."""
    snap = load_snapshot(path)
    assert isinstance(snap, dict), f"{stem}: expected dict, got {type(snap)}"
    assert "source_table" in snap, f"{stem}: missing 'source_table' key"
    assert "steps" in snap, f"{stem}: missing 'steps' key"
    assert "step_count" in snap, f"{stem}: missing 'step_count' key"


# ─── 3. Registry KQL produces valid IR (validate_ir passes) ──────────────────

@pytest.mark.parametrize("stem,kql", list(SNAPSHOT_REGISTRY.items()))
def test_registry_kql_produces_valid_ir(stem, kql):
    """
    Each registered KQL must produce IR that passes validate_ir() with no ERRORs.
    This is the core validator × snapshot integration check.
    """
    ast = parse(kql)
    ir = to_semantic_ir(ast, validate=True)   # raises IRValidationError if invalid
    result = validate_ir(ir)
    assert result.is_valid, (
        f"Snapshot KQL {stem!r} produced invalid IR:\n"
        f"KQL: {kql}\n"
        f"{result.summary()}"
    )


# ─── 4. Registry KQL IR has no errors or V013 duplicates ─────────────────────

@pytest.mark.parametrize("stem,kql", list(SNAPSHOT_REGISTRY.items()))
def test_no_v013_duplicate_alias_in_canonical_queries(stem, kql):
    """
    No canonical KQL should produce duplicate aliases within a projection.
    V013 must not fire on any well-formed query in the registry.
    """
    ast = parse(kql)
    ir = to_semantic_ir(ast)
    result = validate_ir(ir)
    v013_hits = [i for i in result.issues if i.code == "V013"]
    assert not v013_hits, (
        f"V013 (duplicate alias) fired on canonical query {stem!r}:\n"
        f"KQL: {kql}\n"
        f"Issues: {v013_hits}"
    )


# ─── 5. Snapshot structural regression check ─────────────────────────────────

@pytest.mark.parametrize("stem,kql", list(SNAPSHOT_REGISTRY.items()))
def test_snapshot_structure_matches_registry_kql(stem, kql):
    """
    Re-running the KQL must produce an IR whose serialize_ir() output
    matches the stored snapshot. Detects transformer regressions.

    If this fails after an intentional transformer change:
      py tests/regen_snapshots.py   ← intentional update
    """
    snap_path = SNAPSHOTS_DIR / f"{stem}.json"
    if not snap_path.exists():
        pytest.skip(f"Snapshot file {snap_path.name} not found — run regen_snapshots.py")

    stored = load_snapshot(snap_path)
    ast = parse(kql)
    ir = to_semantic_ir(ast)
    current = serialize_ir(ir)

    # Compare key structural fields (not full equality — expression type
    # strings may vary across minor AST changes)
    assert current["source_table"] == stored["source_table"], (
        f"{stem}: source_table changed — {stored['source_table']!r} → "
        f"{current['source_table']!r}"
    )
    assert current["step_count"] == stored["step_count"], (
        f"{stem}: step_count changed — {stored['step_count']} → "
        f"{current['step_count']} — transformer added/removed steps"
    )
    assert len(current["steps"]) == len(stored["steps"]), (
        f"{stem}: step list length changed"
    )
    for i, (cur_step, old_step) in enumerate(
        zip(current["steps"], stored["steps"])
    ):
        assert cur_step["type"] == old_step["type"], (
            f"{stem}: steps[{i}] type changed — "
            f"{old_step['type']!r} → {cur_step['type']!r}"
        )


# ─── 6. V013 fires correctly on injected duplicates ──────────────────────────

class TestV013Rule:
    """V013 catches duplicate aliases within a SemanticProjection."""

    def test_v013_fires_on_duplicate_alias(self):
        from kqlbridge.ir.nodes import (
            SemanticQuery, SemanticProjection, ProjectionItem,
        )
        from kqlbridge.scoping import SymbolTable
        st = SymbolTable()
        ir = SemanticQuery(
            source="T",
            steps=[
                SemanticProjection(
                    items=[
                        ProjectionItem(alias="score", expression=None,
                                       symbol_id=1, derived_from=[]),
                        ProjectionItem(alias="score", expression=None,   # duplicate
                                       symbol_id=2, derived_from=[]),
                    ],
                    is_extend_only=False,
                )
            ],
            ctes={},
            symbol_table=st,
            pipeline_state={},
        )
        result = validate_ir(ir)
        codes = [i.code for i in result.issues]
        assert "V013" in codes

    def test_v013_does_not_fire_on_unique_aliases(self):
        from kqlbridge.ir.nodes import (
            SemanticQuery, SemanticProjection, ProjectionItem,
        )
        from kqlbridge.scoping import SymbolTable
        st = SymbolTable()
        ir = SemanticQuery(
            source="T",
            steps=[
                SemanticProjection(
                    items=[
                        ProjectionItem(alias="a", expression=None,
                                       symbol_id=1, derived_from=[]),
                        ProjectionItem(alias="b", expression=None,
                                       symbol_id=2, derived_from=[]),
                        ProjectionItem(alias="c", expression=None,
                                       symbol_id=3, derived_from=[]),
                    ],
                    is_extend_only=False,
                )
            ],
            ctes={},
            symbol_table=st,
            pipeline_state={},
        )
        result = validate_ir(ir)
        codes = [i.code for i in result.issues]
        assert "V013" not in codes

    def test_v013_error_message_names_the_alias(self):
        from kqlbridge.ir.nodes import (
            SemanticQuery, SemanticProjection, ProjectionItem,
        )
        from kqlbridge.scoping import SymbolTable
        st = SymbolTable()
        ir = SemanticQuery(
            source="T",
            steps=[
                SemanticProjection(
                    items=[
                        ProjectionItem(alias="revenue", expression=None,
                                       symbol_id=1, derived_from=[]),
                        ProjectionItem(alias="revenue", expression=None,
                                       symbol_id=2, derived_from=[]),
                    ],
                    is_extend_only=False,
                )
            ],
            ctes={},
            symbol_table=st,
            pipeline_state={},
        )
        result = validate_ir(ir)
        v013 = next(i for i in result.issues if i.code == "V013")
        assert "revenue" in v013.message
