[CmdletBinding()]
param(
    [Parameter()]
    [string] $ApiKey = "",

    [Parameter()]
    [string] $ApiSecret = "",

    [Parameter()]
    [string] $Label = "binance-live",

    [switch] $PersistUser
)

$ErrorActionPreference = "Stop"

function Get-EffectiveEnvValue {
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

function Set-ScopedEnvValue {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Name,

        [Parameter(Mandatory = $true)]
        [string] $Value,

        [switch] $PersistToUser
    )

    [Environment]::SetEnvironmentVariable($Name, $Value, "Process")
    if ($PersistToUser) {
        [Environment]::SetEnvironmentVariable($Name, $Value, "User")
    }
}

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    $ApiKey = Get-EffectiveEnvValue -Name "BINANCE_API_KEY"
}
if ([string]::IsNullOrWhiteSpace($ApiSecret)) {
    $ApiSecret = Get-EffectiveEnvValue -Name "BINANCE_API_SECRET"
}

if ([string]::IsNullOrWhiteSpace($ApiKey) -or [string]::IsNullOrWhiteSpace($ApiSecret)) {
    throw "BINANCE_API_KEY and BINANCE_API_SECRET must be provided explicitly or already exist in the environment."
}

Set-ScopedEnvValue -Name "BINANCE_API_KEY" -Value $ApiKey -PersistToUser:$PersistUser
Set-ScopedEnvValue -Name "BINANCE_API_SECRET" -Value $ApiSecret -PersistToUser:$PersistUser
Set-ScopedEnvValue -Name "V53_BINANCE_API_KEY" -Value $ApiKey -PersistToUser:$PersistUser
Set-ScopedEnvValue -Name "V53_BINANCE_SECRET_KEY" -Value $ApiSecret -PersistToUser:$PersistUser

if (-not [string]::IsNullOrWhiteSpace($Label)) {
    Set-ScopedEnvValue -Name "V53_BINANCE_LABEL" -Value $Label -PersistToUser:$PersistUser
}

$scope = if ($PersistUser) { "process+user" } else { "process_only" }

[ordered]@{
    installed = $true
    scope = $scope
    label = $Label
    env_names = @(
        "BINANCE_API_KEY",
        "BINANCE_API_SECRET",
        "V53_BINANCE_API_KEY",
        "V53_BINANCE_SECRET_KEY",
        "V53_BINANCE_LABEL"
    )
    api_key_length = $ApiKey.Length
    api_secret_length = $ApiSecret.Length
} | ConvertTo-Json -Depth 4
