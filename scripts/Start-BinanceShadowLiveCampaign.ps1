[CmdletBinding()]
param(
    [Parameter()]
    [string] $RepoRoot = "",

    [Parameter()]
    [string] $CampaignRoot = "",

    [Parameter()]
    [string[]] $Pairs = @("BTCUSDT", "ETHUSDT"),

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
    [switch] $SkipServiceLaunch,
    [switch] $SkipDashboardRender,
    [switch] $StopOnError,

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
$dashboardOutputDir = Join-Path $CampaignRoot "technical_dashboard"
$configPath = Join-Path $CampaignRoot "live_websocket_config.json"

New-Item -ItemType Directory -Force -Path @(
    $CampaignRoot,
    $serviceDir,
    $orchestratorDir,
    $shadowSessionDir,
    $liveCapturesRoot,
    $autoExportsRoot,
    $dashboardOutputDir
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

$routeHints = @{}
if ($existingConfig.ContainsKey("route_hints_by_pair") -and $existingConfig["route_hints_by_pair"] -is [hashtable]) {
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
        "--max-cycles", "1",
        "--poll-interval-s", "0"
    )
    if ($StopOnError) {
        $serviceArgs += "--stop-on-error"
    }

    & python @serviceArgs
    if ($LASTEXITCODE -ne 0) {
        throw "run_shadow_vps_service.py exited with code $LASTEXITCODE"
    }
}

if (-not $SkipDashboardRender) {
    & python "scripts/run_technical_dashboard.py" `
        "--output-dir" $dashboardOutputDir `
        "--local-runtime-root" $CampaignRoot
    if ($LASTEXITCODE -ne 0) {
        throw "run_technical_dashboard.py exited with code $LASTEXITCODE"
    }
}

[ordered]@{
    campaign_root = [System.IO.Path]::GetFullPath($CampaignRoot)
    live_websocket_config = [System.IO.Path]::GetFullPath($configPath)
    service_dir = [System.IO.Path]::GetFullPath($serviceDir)
    dashboard_html = [System.IO.Path]::GetFullPath((Join-Path $dashboardOutputDir "technical_dashboard.html"))
    user_data_stream_enabled = $hasAuthenticatedUserData
    execution_runtime_projection_path_ref = $configPayload["execution_runtime_projection_path_ref"]
    regime_lite_assessment_path_ref = $configPayload["regime_lite_assessment_path_ref"]
    regime_lite_safing_recommendation_path_ref = $configPayload["regime_lite_safing_recommendation_path_ref"]
    service_launched = (-not $SkipServiceLaunch)
    dashboard_rendered = (-not $SkipDashboardRender)
} | ConvertTo-Json -Depth 8
