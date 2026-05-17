[CmdletBinding()]
param(
    [Parameter()]
    [string] $RepoRoot = "",

    [Parameter()]
    [string] $CampaignRoot = "",

    [Parameter()]
    [string[]] $Pairs = @(),

    [Parameter()]
    [string[]] $StreamTypes = @("trade", "ticker"),

    [Parameter()]
    [string] $SessionDate = "",

    [Parameter()]
    [string] $ApiKey = "",

    [Parameter()]
    [string] $ApiSecret = "",

    [switch] $PersistUserEnv,
    [switch] $PublicOnly,
    [switch] $EnableTimeSyncProbe,
    [switch] $EnableExecutionRuntimeBootstrap,
    [switch] $SkipServiceLaunch,
    [switch] $SkipDashboardRender,
    [switch] $StopOnError,

    # 0 = unlimited (runs until Ctrl+C / SIGTERM); positive = exact cycle cap.
    # Default of 1 preserves the original one-shot warmup behaviour.
    [Parameter()]
    [int] $MaxCycles = 1,

    [Parameter()]
    [double] $PollIntervalS = 0.0,

    [Parameter()]
    [string] $ExecutionRuntimeProjectionPath = "",

    [Parameter()]
    [string] $RegimeLiteAssessmentPath = "",

    [Parameter()]
    [string] $RegimeLiteSafingRecommendationPath = ""
)

$ErrorActionPreference = "Stop"

function Resolve-RepoPath {
    param(
        [Parameter(Mandatory = $true)]
        [string] $BasePath,

        [Parameter(Mandatory = $true)]
        [string] $ChildPath
    )

    return [System.IO.Path]::GetFullPath((Join-Path $BasePath $ChildPath))
}

function ConvertTo-PlainHashtable {
    param(
        [Parameter()]
        $InputObject
    )

    if ($null -eq $InputObject) {
        return $null
    }
    if ($InputObject -is [System.Collections.IDictionary]) {
        $table = @{}
        foreach ($key in $InputObject.Keys) {
            $table[$key] = ConvertTo-PlainHashtable -InputObject $InputObject[$key]
        }
        return $table
    }
    if (
        ($InputObject -is [System.Collections.IEnumerable]) `
        -and -not ($InputObject -is [string])
    ) {
        $items = @()
        foreach ($item in $InputObject) {
            $items += ,(ConvertTo-PlainHashtable -InputObject $item)
        }
        return $items
    }
    if ($InputObject -is [pscustomobject]) {
        $table = @{}
        foreach ($property in $InputObject.PSObject.Properties) {
            $table[$property.Name] = ConvertTo-PlainHashtable -InputObject $property.Value
        }
        return $table
    }
    return $InputObject
}

function Get-ExistingEnvValue {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Name
    )

    $processValue = [Environment]::GetEnvironmentVariable($Name, "Process")
    if (-not [string]::IsNullOrWhiteSpace($processValue)) {
        return $processValue
    }
    return [Environment]::GetEnvironmentVariable($Name, "User")
}

function Resolve-OptionalArtifactRef {
    param(
        [Parameter()]
        [string] $PathValue
    )

    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        return ""
    }
    return [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $PathValue).Path)
}

function Get-RouteHintPayloads {
    param(
        [Parameter()]
        $RouteHintEntry
    )

    if ($RouteHintEntry -is [System.Collections.IDictionary]) {
        return @($RouteHintEntry)
    }
    if (
        ($RouteHintEntry -is [System.Collections.IEnumerable]) `
        -and -not ($RouteHintEntry -is [string])
    ) {
        $payloads = @()
        foreach ($item in $RouteHintEntry) {
            if ($item -is [System.Collections.IDictionary]) {
                $payloads += ,$item
            }
        }
        return $payloads
    }
    return @()
}

function Test-PairScopeMatches {
    param(
        [Parameter()]
        [string[]] $ExpectedPairs,

        [Parameter()]
        $CandidatePairs
    )

    if (-not ($CandidatePairs -is [System.Collections.IEnumerable]) -or ($CandidatePairs -is [string])) {
        return $false
    }

    $resolved = @()
    foreach ($item in $CandidatePairs) {
        $pair = [string]$item
        if ([string]::IsNullOrWhiteSpace($pair)) {
            continue
        }
        $resolved += $pair.ToUpperInvariant()
    }

    if ($resolved.Count -ne $ExpectedPairs.Count) {
        return $false
    }
    for ($index = 0; $index -lt $ExpectedPairs.Count; $index += 1) {
        if ($resolved[$index] -ne $ExpectedPairs[$index].ToUpperInvariant()) {
            return $false
        }
    }
    return $true
}

function Test-RouteHintsCoverExpectedPlan {
    param(
        [Parameter()]
        $RouteHints,

        [Parameter()]
        $ExpectedRouteHints
    )

    if (-not ($RouteHints -is [System.Collections.IDictionary])) {
        return $false
    }
    if (-not ($ExpectedRouteHints -is [System.Collections.IDictionary])) {
        return $false
    }

    foreach ($pairKey in $ExpectedRouteHints.Keys) {
        if (-not $RouteHints.Contains($pairKey)) {
            return $false
        }
        $expectedEngineIds = New-Object 'System.Collections.Generic.HashSet[string]'
        foreach ($expectedPayload in (Get-RouteHintPayloads -RouteHintEntry $ExpectedRouteHints[$pairKey])) {
            $engineId = [string]$expectedPayload["engine_id"]
            if (-not [string]::IsNullOrWhiteSpace($engineId)) {
                [void]$expectedEngineIds.Add($engineId)
            }
        }
        $actualEngineIds = New-Object 'System.Collections.Generic.HashSet[string]'
        foreach ($actualPayload in (Get-RouteHintPayloads -RouteHintEntry $RouteHints[$pairKey])) {
            $engineId = [string]$actualPayload["engine_id"]
            if (-not [string]::IsNullOrWhiteSpace($engineId)) {
                [void]$actualEngineIds.Add($engineId)
            }
        }
        foreach ($engineId in $expectedEngineIds) {
            if (-not $actualEngineIds.Contains($engineId)) {
                return $false
            }
        }
    }
    return $true
}

function Get-ShadowLivePlan {
    param(
        [Parameter(Mandatory = $true)]
        [string] $PlanScriptPath,

        [Parameter()]
        [string[]] $RequestedPairs = @()
    )

    $args = @($PlanScriptPath)
    if ($RequestedPairs.Count -gt 0) {
        $args += "--pairs"
        $args += $RequestedPairs
    }
    $payload = & python @args
    if ($LASTEXITCODE -ne 0) {
        throw "build_shadow_live_plan.py exited with code $LASTEXITCODE"
    }
    return ConvertTo-PlainHashtable -InputObject ($payload | ConvertFrom-Json)
}

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
}
if ([string]::IsNullOrWhiteSpace($CampaignRoot)) {
    $CampaignRoot = Resolve-RepoPath -BasePath $RepoRoot -ChildPath "build\build11_live_websocket_campaign"
}

$serviceDir = Join-Path $CampaignRoot "service"
$orchestratorDir = Join-Path $CampaignRoot "orchestrator"
$shadowSessionDir = Join-Path $CampaignRoot "shadow_session"
$liveCapturesRoot = Join-Path $CampaignRoot "live_captures"
$autoExportsRoot = Join-Path $CampaignRoot "auto_exports"
$dashboardCommandQueueRoot = Join-Path $serviceDir "dashboard_command_queue"
$servicePidFile = Join-Path $serviceDir "shadow_vps_service.pid"
$configPath = Join-Path $CampaignRoot "live_websocket_config.json"
$planScriptPath = Join-Path $PSScriptRoot "build_shadow_live_plan.py"

New-Item -ItemType Directory -Force -Path @(
    $CampaignRoot,
    $serviceDir,
    $orchestratorDir,
    $shadowSessionDir,
    $liveCapturesRoot,
    $autoExportsRoot,
    $dashboardCommandQueueRoot
) | Out-Null

if (-not [string]::IsNullOrWhiteSpace($ApiKey) -or -not [string]::IsNullOrWhiteSpace($ApiSecret) -or $PersistUserEnv) {
    & (Join-Path $PSScriptRoot "Install-BinanceApiEnv.ps1") `
        -ApiKey $ApiKey `
        -ApiSecret $ApiSecret `
        -PersistUser:$PersistUserEnv | Out-Null
}

$effectiveApiKey = Get-ExistingEnvValue -Name "BINANCE_API_KEY"
$effectiveApiSecret = Get-ExistingEnvValue -Name "BINANCE_API_SECRET"
$hasAuthenticatedUserData = (
    -not $PublicOnly `
    -and -not [string]::IsNullOrWhiteSpace($effectiveApiKey) `
    -and -not [string]::IsNullOrWhiteSpace($effectiveApiSecret)
)

if ((-not $PublicOnly) -and (-not $hasAuthenticatedUserData)) {
    Write-Warning "BINANCE_API_KEY/BINANCE_API_SECRET are not both available; the launch will stay public-market-only."
}

$existingConfig = @{}
if (Test-Path -LiteralPath $configPath) {
    $loaded = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
    if ($null -ne $loaded) {
        $existingConfig = ConvertTo-PlainHashtable -InputObject $loaded
    }
}

$requestedPairs = @()
foreach ($pair in $Pairs) {
    $resolvedPair = [string]$pair
    if ([string]::IsNullOrWhiteSpace($resolvedPair)) {
        continue
    }
    $requestedPairs += $resolvedPair.ToUpperInvariant()
}
$livePlan = Get-ShadowLivePlan -PlanScriptPath $planScriptPath -RequestedPairs $requestedPairs
$Pairs = @($livePlan["pairs"])
$routeHints = $livePlan["route_hints_by_pair"]
if (
    $existingConfig.ContainsKey("pairs") `
    -and (Test-PairScopeMatches -ExpectedPairs $Pairs -CandidatePairs $existingConfig["pairs"]) `
    -and $existingConfig.ContainsKey("route_hints_by_pair") `
    -and (Test-RouteHintsCoverExpectedPlan `
        -RouteHints $existingConfig["route_hints_by_pair"] `
        -ExpectedRouteHints $routeHints)
) {
    $routeHints = $existingConfig["route_hints_by_pair"]
}

$strategyConfig = @{
    strategy_id = "strategy-shadow-vps-live"
    strategy_version = "a.v4.2"
    lineage_version = "a.v4.2.r1"
    strategy_classification = "a_variant"
    performance_mode = "research_fast_mode"
}
if ($existingConfig.ContainsKey("config") -and $existingConfig["config"] -is [hashtable]) {
    $strategyConfig = $existingConfig["config"]
}

$configPayload = [ordered]@{
    endpoint = if ($existingConfig.ContainsKey("endpoint")) { $existingConfig["endpoint"] } else { "wss://stream.binance.com:9443/ws" }
    pairs = $Pairs
    stream_types = $StreamTypes
    capture_frame_limit = if ($existingConfig.ContainsKey("capture_frame_limit")) { $existingConfig["capture_frame_limit"] } else { 8 }
    idle_poll_limit = if ($existingConfig.ContainsKey("idle_poll_limit")) { $existingConfig["idle_poll_limit"] } else { 6 }
    capture_timeout_s = if ($existingConfig.ContainsKey("capture_timeout_s")) { $existingConfig["capture_timeout_s"] } else { 5.0 }
    time_sync_probe_enabled = [bool]$EnableTimeSyncProbe
    execution_runtime_bootstrap_enabled = [bool]$EnableExecutionRuntimeBootstrap
    time_sync_sample_count = if ($existingConfig.ContainsKey("time_sync_sample_count")) { $existingConfig["time_sync_sample_count"] } else { 3 }
    execution_runtime_projection_path_ref = if ([string]::IsNullOrWhiteSpace($ExecutionRuntimeProjectionPath)) {
        if ($existingConfig.ContainsKey("execution_runtime_projection_path_ref")) { $existingConfig["execution_runtime_projection_path_ref"] } else { "" }
    } else {
        Resolve-OptionalArtifactRef -PathValue $ExecutionRuntimeProjectionPath
    }
    regime_lite_assessment_path_ref = if ([string]::IsNullOrWhiteSpace($RegimeLiteAssessmentPath)) {
        if ($existingConfig.ContainsKey("regime_lite_assessment_path_ref")) { $existingConfig["regime_lite_assessment_path_ref"] } else { "" }
    } else {
        Resolve-OptionalArtifactRef -PathValue $RegimeLiteAssessmentPath
    }
    regime_lite_safing_recommendation_path_ref = if ([string]::IsNullOrWhiteSpace($RegimeLiteSafingRecommendationPath)) {
        if ($existingConfig.ContainsKey("regime_lite_safing_recommendation_path_ref")) { $existingConfig["regime_lite_safing_recommendation_path_ref"] } else { "" }
    } else {
        Resolve-OptionalArtifactRef -PathValue $RegimeLiteSafingRecommendationPath
    }
    user_data_stream_enabled = $hasAuthenticatedUserData
    user_data_endpoint = if ($existingConfig.ContainsKey("user_data_endpoint")) { $existingConfig["user_data_endpoint"] } else { "wss://ws-api.binance.com:443/ws-api/v3" }
    user_data_api_key_env_var = "BINANCE_API_KEY"
    user_data_api_secret_env_var = "BINANCE_API_SECRET"
    user_data_recv_window_ms = if ($existingConfig.ContainsKey("user_data_recv_window_ms")) { $existingConfig["user_data_recv_window_ms"] } else { 5000 }
    user_data_capture_timeout_s = if ($existingConfig.ContainsKey("user_data_capture_timeout_s")) { $existingConfig["user_data_capture_timeout_s"] } else { 10.0 }
    user_data_idle_poll_limit = if ($existingConfig.ContainsKey("user_data_idle_poll_limit")) { $existingConfig["user_data_idle_poll_limit"] } else { 10 }
    user_data_event_limit = if ($existingConfig.ContainsKey("user_data_event_limit")) { $existingConfig["user_data_event_limit"] } else { 10 }
    session_date_override = $SessionDate
    route_hints_by_pair = $routeHints
    config = $strategyConfig
}

$configPayload | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $configPath -Encoding UTF8

if (-not $SkipServiceLaunch) {
    $serviceArgs = @(
        "scripts/run_shadow_vps_service.py",
        "--service-dir", $serviceDir,
        "--orchestrator-output-dir", $orchestratorDir,
        "--shadow-output-dir", $shadowSessionDir,
        "--live-websocket-config", $configPath,
        "--live-captures-root", $liveCapturesRoot,
        "--auto-exports-root", $autoExportsRoot,
        "--dashboard-command-queue-root", $dashboardCommandQueueRoot,
        "--pid-file", $servicePidFile,
        "--poll-interval-s", "$PollIntervalS"
    )
    if ($MaxCycles -gt 0) {
        $serviceArgs += @("--max-cycles", "$MaxCycles")
    }
    # MaxCycles = 0 → omit --max-cycles entirely → service runs until Ctrl+C / SIGTERM
    if ($StopOnError) {
        $serviceArgs += "--stop-on-error"
    }

    & python @serviceArgs
    if ($LASTEXITCODE -ne 0) {
        throw "run_shadow_vps_service.py exited with code $LASTEXITCODE"
    }
}

[ordered]@{
    campaign_root = [System.IO.Path]::GetFullPath($CampaignRoot)
    live_websocket_config = [System.IO.Path]::GetFullPath($configPath)
    service_dir = [System.IO.Path]::GetFullPath($serviceDir)
    service_pid_file = [System.IO.Path]::GetFullPath($servicePidFile)
    dashboard_command_queue_root = [System.IO.Path]::GetFullPath($dashboardCommandQueueRoot)
    observability_export = [System.IO.Path]::GetFullPath((Join-Path $serviceDir "shadow_vps_service_observability_export.json"))
    observability_prom = [System.IO.Path]::GetFullPath((Join-Path $serviceDir "shadow_vps_service_observability.prom"))
    scrape_manifest = [System.IO.Path]::GetFullPath((Join-Path $serviceDir "shadow_vps_service_scrape_manifest.json"))
    prometheus_file_sd = [System.IO.Path]::GetFullPath((Join-Path $serviceDir "shadow_vps_service_prometheus_file_sd.json"))
    user_data_stream_enabled = $hasAuthenticatedUserData
    execution_runtime_projection_path_ref = $configPayload["execution_runtime_projection_path_ref"]
    regime_lite_assessment_path_ref = $configPayload["regime_lite_assessment_path_ref"]
    regime_lite_safing_recommendation_path_ref = $configPayload["regime_lite_safing_recommendation_path_ref"]
    service_launched = (-not $SkipServiceLaunch)
    dashboard_rendered = $false
} | ConvertTo-Json -Depth 8
