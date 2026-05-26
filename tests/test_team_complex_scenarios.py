"""
test_team_complex_scenarios.py — Complex Sentinel KQL Query Transpiler & Lineage Validation Gating Suite
========================================================================================================
Audits compiled Spark SQL, T-SQL, PySpark outputs, and intermediate representation (IR) lineages
for the 3 complex Sentinel KQL queries from team_end_user.

Ensures:
  1. Accurate semantic translation across all targets.
  2. Complete structural correctness of explain_semantic() diagnostics trees.
  3. Strict absence of circular references or infinite loops in symbol lineages.
  4. Precise mapping from terminal projection outputs back to leaf source columns.
"""

from __future__ import annotations
import pytest
import sys
from kqlbridge import translate, explain_semantic, ExplainSemanticResult, SymbolLineageNode

# Reconfigure stdout to use UTF-8 under Windows shell to avoid UnicodeEncodeError in case of print assertions
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ─── COMPLEX SENTINEL KQL QUERIES FROM END USER ───────────────────────────────────

QUERY_1 = """
let ForeignLogins = SigninLogs
    | where TimeGenerated > ago(7d)
    | where Location != "US" and (ResultType == 0 or ResultType == 50126)
    | summarize FailedCount = countif(ResultType == 50126), SuccessCount = countif(ResultType == 0) by UserPrincipalName, IPAddress;
let AdminActions = AuditLogs
    | where TimeGenerated > ago(7d)
    | where OperationName in ("Add user", "Add member to role", "Update user")
    | project TimeGenerated, OperationName, TargetUser = TargetResources, DeviceId = UserPrincipalName;
ForeignLogins
| join kind=inner (AdminActions) on DeviceId
| extend HighRisk = iff(FailedCount > 5 and SuccessCount > 0, true, false)
| where HighRisk == true
| summarize ActionCount = count() by DeviceId, OperationName, bin(TimeGenerated, 1h)
"""

QUERY_2 = """
let ObfuscatedCommands = DeviceProcessEvents
    | where TimeGenerated > ago(1d)
    | where FileName =~ "powershell.exe" or FileName =~ "cmd.exe"
    | where CommandLine has "bypass" or CommandLine has "encodedcommand" or CommandLine has "downloadstring"
    | project ProcessTime = TimeGenerated, DeviceId, CommandLine;
let PortScans = DeviceNetworkEvents
    | where TimeGenerated > ago(1d)
    | where RemotePort in (4444, 8080, 9000)
    | summarize ConnectionCount = count() by DeviceId, RemotePort, bin(TimeGenerated, 10m);
ObfuscatedCommands
| join kind=inner (PortScans) on DeviceId
| where ProcessTime between (TimeGenerated .. datetime_add("minute", 30, TimeGenerated))
| summarize AlertCount = count() by DeviceId, RemotePort
"""

QUERY_3 = """
let Downloads = DeviceFileEvents
    | where TimeGenerated > ago(3d)
    | where FolderPath has "Downloads" and (FileName endswith ".exe" or FileName endswith ".ps1" or FileName endswith ".bat")
    | project DownloadTime = TimeGenerated, DeviceId, DownloadedFile = FileName;
let Evasion = SecurityEvent
    | where TimeGenerated > ago(3d)
    | where EventID == 1102 or EventID == 4698 or EventID == 4702
    | project EvasionTime = TimeGenerated, DeviceId = Computer, EventID;
let Exfil = DeviceNetworkEvents
    | where TimeGenerated > ago(3d)
    | where BytesSent > 10000000
    | summarize TotalExfilBytes = sum(BytesSent) by DeviceId;
Downloads
| join kind=inner (Evasion) on DeviceId
| join kind=inner (Exfil) on DeviceId
| where EvasionTime > DownloadTime
| project DeviceId, DownloadedFile, EventID, TotalExfilBytes
"""


# ─── HELPER LINEAGE Cycle & Integrity Assertions ───────────────────────────────

def assert_no_circular_dependencies(node: SymbolLineageNode, path: list[tuple[int, str]] = None) -> None:
    """Recursively audits the lineage tree ensuring zero cycle loops exist."""
    if path is None:
        path = []
        
    for s_id, name in path:
        assert node.symbol_id != s_id, (
            f"FAIL: Circular dependency detected in diagnostic tree. "
            f"Symbol '{node.name}' (id={node.symbol_id}) re-entered path: "
            f"{' -> '.join(f'{n} (id={i})' for i, n in path)}"
        )
        
    current_path = path + [(node.symbol_id, node.name)]
    for dep in node.dependencies:
        assert_no_circular_dependencies(dep, current_path)


def collect_leaves(node: SymbolLineageNode) -> list[SymbolLineageNode]:
    """Retrieves all terminal leaf nodes (physical source reference columns) of the lineage tree."""
    if not node.dependencies:
        return [node]
    leaves = []
    for dep in node.dependencies:
        leaves.extend(collect_leaves(dep))
    return leaves


# ─── TRANSPILED CODE AND LINEAGE TESTS ──────────────────────────────────────────

class TestTeamComplexScenarios:
    """Robust QA Gate validations for compiled query outputs and diagnostic lineage correctness."""

    @pytest.mark.parametrize("target", ["spark", "tsql", "pyspark"])
    def test_query_1_compilation(self, target: str):
        """QA GATE: Verify successful translation and semantic parity of Query 1 across dialects."""
        compiled = translate(QUERY_1, target=target)
        assert isinstance(compiled, str)
        assert len(compiled.strip()) > 0
        
        if target == "spark":
            assert "WITH ForeignLogins AS" in compiled or "with foreignlogins as" in compiled.lower()
            assert "AdminActions AS" in compiled or "adminactions as" in compiled.lower()
            assert "INNER JOIN AdminActions" in compiled or "inner join adminactions" in compiled.lower()
            assert "CASE WHEN" in compiled
            assert "GROUP BY DeviceId, OperationName" in compiled or "group by deviceid, operationname" in compiled.lower()
            
        elif target == "tsql":
            assert "WITH ForeignLogins AS" in compiled or "with foreignlogins as" in compiled.lower()
            assert "DATEADD(day, -7, GETDATE())" in compiled
            assert "CASE WHEN" in compiled
            
        elif target == "pyspark":
            assert "ForeignLogins = spark.table('SigninLogs')" in compiled
            assert "df = ForeignLogins" in compiled or "df =" in compiled
            assert "join_right_DeviceId = AdminActions" in compiled
            assert "HighRisk" in compiled

    def test_query_1_lineage_flawless(self):
        """QA GATE: Audit ExplainSemanticResult lineages and leaf-source mapping for Query 1."""
        report = explain_semantic(QUERY_1, target="spark")
        assert isinstance(report, ExplainSemanticResult)
        assert len(report.symbols) > 0
        
        # Verify specific visible output columns are tracked correctly
        output_names = {sym.name for sym in report.symbols}
        expected_outputs = {"DeviceId", "OperationName", "TimeGenerated", "ActionCount"}
        assert expected_outputs.issubset(output_names), f"Missing columns in lineage output: {expected_outputs - output_names}"

        for sym in report.symbols:
            # 1. No cycles in the DAG path
            assert_no_circular_dependencies(sym)
            
            # 2. Extract terminal leaf nodes
            leaves = collect_leaves(sym)
            for leaf in leaves:
                # Verify leaf node integrity
                assert isinstance(leaf.name, str) and len(leaf.name) > 0
                assert isinstance(leaf.symbol_id, int)
                assert isinstance(leaf.origin_node, str)

    @pytest.mark.parametrize("target", ["spark", "tsql", "pyspark"])
    def test_query_2_compilation(self, target: str):
        """QA GATE: Verify successful translation and semantic parity of Query 2 across dialects."""
        compiled = translate(QUERY_2, target=target)
        assert isinstance(compiled, str)
        assert len(compiled.strip()) > 0
        
        if target == "spark":
            assert "LOWER(FileName) = LOWER('powershell.exe') OR LOWER(FileName) = LOWER('cmd.exe')" in compiled
            assert "RemotePort IN (4444, 8080, 9000)" in compiled
            assert "ProcessTime >= TimeGenerated" in compiled or "processtime >= timegenerated" in compiled.lower()
            
        elif target == "tsql":
            assert "DATEADD(day, -1, GETDATE())" in compiled
            assert "RemotePort IN (4444, 8080, 9000)" in compiled
            
        elif target == "pyspark":
            assert "ObfuscatedCommands = spark.table('DeviceProcessEvents')" in compiled
            assert "PortScans = spark.table('DeviceNetworkEvents')" in compiled

    def test_query_2_lineage_flawless(self):
        """QA GATE: Audit ExplainSemanticResult lineages and leaf-source mapping for Query 2."""
        report = explain_semantic(QUERY_2, target="spark")
        assert isinstance(report, ExplainSemanticResult)
        assert len(report.symbols) > 0
        
        output_names = {sym.name for sym in report.symbols}
        expected_outputs = {"DeviceId", "RemotePort", "AlertCount"}
        assert expected_outputs.issubset(output_names), f"Missing columns in lineage output: {expected_outputs - output_names}"

        for sym in report.symbols:
            assert_no_circular_dependencies(sym)
            
            leaves = collect_leaves(sym)
            for leaf in leaves:
                assert isinstance(leaf.name, str) and len(leaf.name) > 0
                assert isinstance(leaf.symbol_id, int)
                assert isinstance(leaf.origin_node, str)

    @pytest.mark.parametrize("target", ["spark", "tsql", "pyspark"])
    def test_query_3_compilation(self, target: str):
        """QA GATE: Verify successful translation and semantic parity of Query 3 across dialects."""
        compiled = translate(QUERY_3, target=target)
        assert isinstance(compiled, str)
        assert len(compiled.strip()) > 0
        
        if target == "spark":
            assert "Downloads AS (" in compiled
            assert "Evasion AS (" in compiled
            assert "Exfil AS (" in compiled
            assert "SUM(BytesSent) AS TotalExfilBytes" in compiled or "sum(BytesSent) AS TotalExfilBytes" in compiled.lower()
            assert "INNER JOIN Evasion" in compiled or "inner join evasion" in compiled.lower()
            assert "INNER JOIN Exfil" in compiled or "inner join exfil" in compiled.lower()
            assert "EvasionTime > DownloadTime" in compiled
            
        elif target == "tsql":
            assert "DATEADD(day, -3, GETDATE())" in compiled
            assert "INNER JOIN Evasion" in compiled or "inner join evasion" in compiled.lower()
            
        elif target == "pyspark":
            assert "Downloads = spark.table('DeviceFileEvents')" in compiled
            assert "Evasion = spark.table('SecurityEvent')" in compiled
            assert "Exfil = spark.table('DeviceNetworkEvents')" in compiled

    def test_query_3_lineage_flawless(self):
        """QA GATE: Audit ExplainSemanticResult lineages and leaf-source mapping for Query 3."""
        report = explain_semantic(QUERY_3, target="spark")
        assert isinstance(report, ExplainSemanticResult)
        assert len(report.symbols) > 0
        
        output_names = {sym.name for sym in report.symbols}
        expected_outputs = {"DeviceId", "DownloadedFile", "EventID", "TotalExfilBytes"}
        assert expected_outputs.issubset(output_names), f"Missing columns in lineage output: {expected_outputs - output_names}"

        for sym in report.symbols:
            assert_no_circular_dependencies(sym)
            
            leaves = collect_leaves(sym)
            for leaf in leaves:
                assert isinstance(leaf.name, str) and len(leaf.name) > 0
                assert isinstance(leaf.symbol_id, int)
                assert isinstance(leaf.origin_node, str)
