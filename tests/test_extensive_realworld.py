"""
test_extensive_realworld.py — Extensive Real-World KQL to SQL Transpiler Validation Suite
========================================================================================

This test suite validates the transpilation of complex, real-world KQL queries into SQL.
It ensures that the 'kqlbridge' transpiler correctly handles various operators, 
including security, IoT, and adversarial patterns.

Queries marked with xfail are currently known to use unsupported operators or syntax:
- make_set (Query 1)
- !startswith / !contains (Query 2)
- series_fir / series_decompose_anomalies (Query 3)
- arg_max (Query 4)
- hint.strategy (Query 5)
"""

from __future__ import annotations
import pytest
from kqlbridge import translate

# ─── COMPLEX REAL-WORLD KQL QUERIES ───────────────────────────────────────────

QUERY_1 = r"""
let lookback = 24h;
let detectionWindow = 4h;
let failureThreshold = 15;
let suspiciousActivity = SigninLogs
    | where TimeGenerated > ago(lookback)
    | where ResultType != "0"
    | summarize 
        FailureCount = count(), 
        UniqueIPs = dcount(IPAddress), 
        TargetApps = make_set(AppDisplayName),
        EarliestFailure = min(TimeGenerated),
        LatestFailure = max(TimeGenerated)
        by UserPrincipalName
    | where FailureCount >= failureThreshold or UniqueIPs > 3
    | project UserPrincipalName, FailureCount, UniqueIPs, EarliestFailure, LatestFailure;
let successfulBreach = SigninLogs
    | where TimeGenerated > ago(lookback)
    | where ResultType == "0"
    | join kind=inner suspiciousActivity on UserPrincipalName
    | where TimeGenerated between (LatestFailure .. (LatestFailure + detectionWindow))
    | project BreachTime = TimeGenerated, UserPrincipalName, BreachIP = IPAddress, LocationDetails = LocationDetails.city;
AuditLogs
    | where TimeGenerated > ago(lookback)
    | extend Actor = tostring(InitiatedBy.user.userPrincipalName)
    | join kind=inner successfulBreach on $left.Actor == $right.UserPrincipalName
    | where TimeGenerated > BreachTime
    | extend Operation = tostring(OperationName), Target = tostring(TargetResources[0].displayName)
    | where Operation has_any ("Add member to role", "Update user", "Disable MFA", "Delete conditional access policy")
    | summarize 
        PostBreachActions = make_list(Operation), 
        AffectedTargets = make_list(Target),
        ActionCount = count() 
        by Actor, BreachIP, BreachTime, LocationDetails
    | join kind=leftouter (
        SecurityEvent 
        | where TimeGenerated > ago(lookback) 
        | where EventID == 4624 
        | project Host = Computer, Actor = TargetUserName, LogonType
    ) on Actor
    | project-away Actor1
    | sort by ActionCount desc
"""

QUERY_2 = r"""
let timeframe = 12h;
let correlationMap = AppRequests
    | where TimeGenerated > ago(timeframe)
    | where Name !startswith "GetHeartbeat" and Name !contains "Swagger"
    | project 
        RootOperationId = OperationId, 
        EntryService = AppRoleName, 
        EntryTime = TimeGenerated, 
        OverallDuration = DurationMs;
AppDependencies
    | where TimeGenerated > ago(timeframe)
    | where DependencyType in ("SQL", "HTTP", "Azure Service Bus")
    | join kind=inner correlationMap on $left.OperationId == $right.RootOperationId
    | extend IsSlow = iff(DurationMs > (OverallDuration * 0.7), 1, 0)
    | summarize 
        AvgLatency = avg(DurationMs),
        P95Latency = percentile(DurationMs, 95),
        TotalCalls = count(),
        SlowDependencyCount = sum(IsSlow),
        DependencyList = make_set(Name)
        by RootOperationId, EntryService, EntryTime, Target
    | where P95Latency > 1000
    | join kind=leftouter (
        AppExceptions
        | where TimeGenerated > ago(timeframe)
        | summarize ExceptionCount = count(), Message = any(OuterMessage) by OperationId
    ) on $left.RootOperationId == $right.OperationId
    | extend TimeBin = bin(EntryTime, 15m)
    | project 
        TimeBin, 
        RootOperationId, 
        Target, 
        P95Latency, 
        HealthImpact = iff(ExceptionCount > 0, "Error", iff(SlowDependencyCount > 0, "Degraded", "Healthy")),
        Message
    | sort by TimeBin asc, P95Latency desc
"""

QUERY_3 = r"""
let start = ago(7d);
let end = now();
let step = 15m;
let sensor_metadata = _ResourceId
    | where _ResourceId has "IndustrialHq"
    | parse _ResourceId with * "/resourceGroups/" ResourceGroup "/providers/" *
    | project ResourceGroup, _ResourceId;
IoTTelemetry
    | where TimeGenerated between (start .. end)
    | join kind=inner sensor_metadata on _ResourceId
    | make-series 
        AvgTemp = avg(Temperature), 
        MaxTemp = max(Temperature) 
        on TimeGenerated from start to end step step 
        by DeviceId, ResourceGroup
    | extend SmoothedTemp = series_fir(AvgTemp, repeat(1, 5))
    | extend (Anomalies, Score, Baseline) = series_decompose_anomalies(SmoothedTemp, 2.5, -1, 'linefit')
    | mv-expand TimeGenerated to typeof(datetime), AvgTemp to typeof(double), Anomalies to typeof(long), Score to typeof(double), Baseline to typeof(double)
    | where Anomalies != 0
    | serialize 
    | extend PrevScore = prev(Score)
    | extend ScoreDelta = Score - PrevScore
    | project 
        DeviceId, 
        ResourceGroup, 
        TimeGenerated, 
        CurrentTemp = AvgTemp, 
        ExpectedTemp = Baseline, 
        Severity = abs(Score), 
        IsRising = iff(ScoreDelta > 0, true, false)
    | where Severity > 3.5
    | order by Severity desc
"""

QUERY_4 = r"""
let _threshold = 1.25e-3;
let _pattern = @"^auth-worker-\d{3}\.svc$";
let _lookback = 48h;
let RawEvents = SecurityEvents
    | where TimeGenerated > ago(_lookback)
    | extend NormalizedWeight = coalesce(Weight, 0.0) / 1000.0;
let FilteredNodes = RawEvents
    | where Computer matches regex _pattern
    | summarize arg_max(TimeGenerated, *) by Computer;
let WeightedClusters = RawEvents
    | join kind=inner FilteredNodes on Computer
    | extend IsAnomalous = iff(NormalizedWeight > _threshold, 1, 0)
    | serialize ClusterId = row_number(1, Computer != prev(Computer));
let JoinedAnomalyMap = WeightedClusters
    | where IsAnomalous == 1
    | union (FilteredNodes | extend IsAnomalous = 0, ClusterId = -1)
    | summarize 
        TotalWeight = sum(NormalizedWeight), 
        MaxWeight = max(NormalizedWeight),
        UniqueEvents = count()
      by bin(TimeGenerated, 1h), Computer, ClusterId;
JoinedAnomalyMap
    | join kind=leftouter (WeightedClusters | project Computer, ClusterId, NormalizedWeight) on Computer, ClusterId
    | extend RelativeImpact = NormalizedWeight / (TotalWeight + 1e-9)
    | project TimeGenerated, Computer, RelativeImpact, HealthScore = 1.0 - RelativeImpact
    | where HealthScore < 0.95
    | sort by TimeGenerated asc, HealthScore desc
"""

QUERY_5 = r"""
let _scale = range(1, 5, 1);
let _metaData = AppMetrics
    | summarize hint.strategy=shuffle 
        TagList = make_set(Tags), 
        AvgVal = avg(Value) 
      by Category, Location = tostring(Properties.region);
AppTraces
    | where isnotempty(Properties)
    | extend P = parse_json(Properties)
    | mv-expand _scale
    | extend SubKey = tostring(P.subkeys[toint(_scale - 1)])
    | summarize 
        TraceCount = count(),
        P99 = percentile(todouble(P.latency), 99),
        LastMsg = any(Message)
      by Category = tostring(P.cat), SubKey, bin(TimeGenerated, 5m)
    | join kind=innerhint.strategy=broadcast _metaData on Category
    | mv-expand TagList
    | extend IsMatch = TagList contains SubKey
    | summarize 
        MatchCount = countif(IsMatch),
        GlobalAvg = take_any(AvgVal)
      by Category, tostring(TagList), bin(TimeGenerated, 15m)
    | where MatchCount > 0
    | project Category, Tag = TagList, MatchCount, Efficiency = MatchCount / (GlobalAvg + 1.2e-5)
"""


class TestExtensiveRealWorld:
    """Validation tests for extensive real-world KQL scenarios."""

    @pytest.mark.parametrize("target", ["spark", "tsql"])
    def test_query_1_security_mixed_domains(self, target: str):
        """Validates Query 1: Security patterns with mixed domains and CTEs."""
        compiled = translate(QUERY_1, target=target)
        assert isinstance(compiled, str)
        compiled_lower = compiled.lower()

        # Assertions for Query 1
        assert "suspiciousactivity" in compiled_lower
        assert "successfulbreach" in compiled_lower
        assert "inner join" in compiled_lower
        
        # between must map to >= and <=
        assert ">=" in compiled
        assert "<=" in compiled

    @pytest.mark.parametrize("target", ["spark", "tsql"])
    def test_query_2_log_analytics_mixed_domains(self, target: str):
        """Validates Query 2: Log Analytics with startswith, contains, and percentile."""
        compiled = translate(QUERY_2, target=target)
        assert isinstance(compiled, str)
        compiled_lower = compiled.lower()

        # startswith and contains map to LIKE
        assert "like" in compiled_lower
        
        # percentile(95) handled by dialect function
        if target == "spark":
            assert "percentile" in compiled_lower
        elif target == "tsql":
            assert "percentile_cont" in compiled_lower or "percentile_disc" in compiled_lower
            
        # bin(15m) using timestamp flooring
        # Both Spark and T-SQL often convert 15m to 900 seconds
        assert "900" in compiled or "15" in compiled

    @pytest.mark.xfail(reason="Operator not yet supported: series_fir, series_decompose_anomalies")
    @pytest.mark.parametrize("target", ["spark", "tsql"])
    def test_query_3_iot_mixed_domains(self, target: str):
        """Validates Query 3: IoT telemetry with make-series and time series analysis."""
        compiled = translate(QUERY_3, target=target)
        assert isinstance(compiled, str)
        compiled_lower = compiled.lower()

        # make-series maps to time series table + join
        # prev(Score) maps to LAG
        assert "lag" in compiled_lower
        
        # mv-expand maps to EXPLODE or similar
        if target == "spark":
            assert "explode" in compiled_lower
        elif target == "tsql":
            assert "cross apply" in compiled_lower or "openjson" in compiled_lower

    @pytest.mark.parametrize("target", ["spark", "tsql"])
    def test_query_4_adversarial_kraken(self, target: str):
        """Validates Query 4: Adversarial pattern 'Kraken' with regex and arg_max."""
        compiled = translate(QUERY_4, target=target)
        assert isinstance(compiled, str)
        compiled_lower = compiled.lower()

        # matches regex maps to RLIKE/REGEXP
        if target == "spark":
            assert "rlike" in compiled_lower or "regexp" in compiled_lower
        elif target == "tsql":
            assert "like" in compiled_lower
            
        # 1.25e-3 handled as numeric
        assert "0.00125" in compiled or "1.25e-3" in compiled
        
        # arg_max supported
        if target == "spark":
            assert "max_by" in compiled_lower

    @pytest.mark.parametrize("target", ["spark", "tsql"])
    def test_query_6_k8s_troubleshooting(self, target: str):
        """Scenario 1: K8s Troubleshooting with arg_max and complex join."""
        query = r"""
        let timeRange = ago(24h);
        KubePodInventory
        | where TimeGenerated > timeRange
        | where PodStatus != "Running"
        | summarize arg_max(TimeGenerated, *) by Name, Namespace
        | project PodName = Name, Namespace, PodStatus, ContainerID
        | join kind=inner (
            ContainerLog
            | where TimeGenerated > timeRange
            | where LogEntrySource == "stderr" or Message has "error" or Message has "exception"
        ) on ContainerID
        | project TimeGenerated, PodName, Namespace, PodStatus, Message, LogEntrySource
        | order by TimeGenerated desc
        """
        compiled = translate(query, target=target)
        assert "inner join" in compiled.lower()
        if target == "spark":
            assert "max_by" in compiled.lower()
        assert "containerlog" in compiled.lower()

    @pytest.mark.parametrize("target", ["spark", "tsql"])
    def test_query_7_cloud_governance(self, target: str):
        """Scenario 2: Cloud Governance with arg_max and lookup."""
        query = r"""
        let timeRange = ago(7d);
        SecurityRecommendation
        | where TimeGenerated > timeRange
        | where Severity == "High" and RecommendationState == "Active"
        | summarize arg_max(TimeGenerated, *) by ResourceId
        | project ResourceId, RecommendationName, RecommendationSeverity = Severity
        | lookup (
            AzureActivity
            | where TimeGenerated > timeRange
            | where ActivityStatusValue == "Succeeded"
            | where OperationNameValue has "write" or OperationNameValue has "delete" or OperationNameValue has "action"
        ) on ResourceId
        | project TimeGenerated, ResourceId, OperationNameValue, Caller, RecommendationName, RecommendationSeverity
        | order by TimeGenerated desc
        """
        compiled = translate(query, target=target)
        assert "left outer join" in compiled.lower()
        if target == "spark":
            assert "max_by" in compiled.lower()

    @pytest.mark.parametrize("target", ["spark", "tsql"])
    def test_query_8_web_app_performance(self, target: str):
        """Scenario 3: Web App Performance with complex aggregations."""
        query = r"""
        let slowRequests = 
            AppRequests
            | where TimeGenerated > ago(12h)
            | where Success == false or DurationMs > 1000
            | project TimeGenerated, OperationId, RequestName = Name, RequestDuration = DurationMs, Success;
        AppDependencies
        | where TimeGenerated > ago(12h)
        | join kind=inner slowRequests on OperationId
        | summarize 
            TotalDependencyDuration = sum(DurationMs),
            MaxDependencyDuration = max(DurationMs),
            DependencyCount = count()
            by OperationId, RequestName, RequestDuration, Success
        | project OperationId, RequestName, RequestDuration, TotalDependencyDuration, MaxDependencyDuration, DependencyCount, Success
        | order by RequestDuration desc
        """
        compiled = translate(query, target=target)
        assert "sum(durationms)" in compiled.lower()
        assert "inner join" in compiled.lower()

    @pytest.mark.xfail(reason="Syntax/Operator not yet supported: hint.strategy, make_set")
    @pytest.mark.parametrize("target", ["spark", "tsql"])
    def test_query_5_adversarial_matrix(self, target: str):
        """Validates Query 5: Adversarial pattern 'Matrix' with mv-expand range and parse_json."""
        compiled = translate(QUERY_5, target=target)
        assert isinstance(compiled, str)
        compiled_lower = compiled.lower()

        # mv-expand range produces expansion
        if target == "spark":
            assert "explode" in compiled_lower or "posexplode" in compiled_lower
            
        # hint.strategy handled or ignored
        # parse_json uses native JSON extractor
        if target == "spark":
            assert "get_json_object" in compiled_lower or "json_tuple" in compiled_lower or "from_json" in compiled_lower
        elif target == "tsql":
            assert "json_value" in compiled_lower or "openjson" in compiled_lower
