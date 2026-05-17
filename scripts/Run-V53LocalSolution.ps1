[CmdletBinding()]
param(
    [Parameter()]
    [string] $ApiEnvFile = "",

    [Parameter()]
    [string] $OutputDir = "",

    [Parameter()]
    [string] $CampaignRoot = "",

    [switch] $PublicOnly,
    [switch] $EnableTimeSyncProbe,
    [switch] $EnableExecutionRuntimeBootstrap,
    [switch] $DisableExecutionRuntimeBootstrap,
    [switch] $StopOnError,
    [switch] $SkipServiceLaunch,

    [Parameter()]
    [string] $GrafanaUrl = "http://127.0.0.1:3000",

    [Parameter()]
    [string] $GrafanaUser = "admin",

    [Parameter()]
    [string] $GrafanaPassword = "admin",

    [Parameter()]
    [string] $PrometheusUrl = "http://127.0.0.1:9090",

    [Parameter()]
    [string] $BridgeHost = "127.0.0.1",

    [Parameter()]
    [int] $BridgePort = 19100,

    [Parameter()]
    [string] $PrometheusExe = "C:\tools\prometheus\prometheus-3.9.1.windows-amd64\prometheus.exe",

    [Parameter()]
    [string] $GrafanaServerExe = "C:\tools\grafana\grafana-12.3.1\bin\grafana-server.exe",

    [Parameter()]
    [string] $GrafanaHome = "C:\tools\grafana\grafana-12.3.1",

    [Parameter()]
    [string] $ScrapeInterval = "5s",

    [Parameter()]
    [string] $EvaluationInterval = "5s",

    [Parameter()]
    [double] $ReadinessTimeoutS = 90.0,

    [Parameter()]
    [string] $CockpitHost = "127.0.0.1",

    [Parameter()]
    [int] $CockpitPort = 8080,

    [switch] $NoOpenBrowser
)

$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
if ([string]::IsNullOrWhiteSpace($ApiEnvFile)) {
    $ApiEnvFile = Join-Path $repoRoot ".env"
}
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $repoRoot "build\run_v53_local_solution"
}

$pythonArgs = @(
    "scripts/run_v53_local_solution.py",
    "--api-env-file", $ApiEnvFile,
    "--output-dir", $OutputDir,
    "--grafana-url", $GrafanaUrl,
    "--grafana-user", $GrafanaUser,
    "--grafana-password", $GrafanaPassword,
    "--prometheus-url", $PrometheusUrl,
    "--bridge-host", $BridgeHost,
    "--bridge-port", "$BridgePort",
    "--scrape-interval", $ScrapeInterval,
    "--evaluation-interval", $EvaluationInterval,
    "--readiness-timeout-s", "$ReadinessTimeoutS",
    "--cockpit-host", $CockpitHost,
    "--cockpit-port", "$CockpitPort"
)

if (-not [string]::IsNullOrWhiteSpace($CampaignRoot)) {
    $pythonArgs += @("--campaign-root", $CampaignRoot)
}
if ($PublicOnly) {
    $pythonArgs += "--public-only"
}
if ($EnableTimeSyncProbe) {
    $pythonArgs += "--enable-time-sync-probe"
}
if ($EnableExecutionRuntimeBootstrap) {
    $pythonArgs += "--enable-execution-runtime-bootstrap"
}
if ($DisableExecutionRuntimeBootstrap) {
    $pythonArgs += "--disable-execution-runtime-bootstrap"
}
if ($StopOnError) {
    $pythonArgs += "--stop-on-error"
}
if ($SkipServiceLaunch) {
    $pythonArgs += "--skip-service-launch"
}
if (-not [string]::IsNullOrWhiteSpace($PrometheusExe)) {
    $pythonArgs += @("--prometheus-exe", $PrometheusExe)
}
if (-not [string]::IsNullOrWhiteSpace($GrafanaServerExe)) {
    $pythonArgs += @("--grafana-server-exe", $GrafanaServerExe)
}
if (-not [string]::IsNullOrWhiteSpace($GrafanaHome)) {
    $pythonArgs += @("--grafana-home", $GrafanaHome)
}
if ($NoOpenBrowser) {
    $pythonArgs += "--no-open-browser"
}

Push-Location $repoRoot
try {
    & python @pythonArgs
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
