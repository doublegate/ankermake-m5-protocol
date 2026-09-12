param(
    [string]$ConfigPath = "$env:APPDATA\eufyMake Studio Profile\AnkerMake Studio_23.ini",
    [string]$ExePath = "$env:LOCALAPPDATA\eufyMake Studio\eufymake studio-console.exe",
    [string]$StdoutPath = "$env:TEMP\eufymake_console_trace.out.log",
    [string]$StderrPath = "$env:TEMP\eufymake_console_trace.err.log",
    [int]$AppLogLevel = 5,
    [int]$MqttTraceLevel = 1
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "Config file not found: $ConfigPath"
}

if (-not (Test-Path -LiteralPath $ExePath)) {
    throw "Console executable not found: $ExePath"
}

$config = Get-Content -LiteralPath $ConfigPath
$updated = @()
$seenTraceEnable = $false
$seenTraceLevel = $false

foreach ($line in $config) {
    if ($line -match '^\s*mqtt_trace_enable\s*=') {
        $updated += 'mqtt_trace_enable = 1'
        $seenTraceEnable = $true
        continue
    }
    if ($line -match '^\s*mqtt_trace_level\s*=') {
        $updated += "mqtt_trace_level = $MqttTraceLevel"
        $seenTraceLevel = $true
        continue
    }
    $updated += $line
}

if (-not $seenTraceEnable) {
    $updated += 'mqtt_trace_enable = 1'
}

if (-not $seenTraceLevel) {
    $updated += "mqtt_trace_level = $MqttTraceLevel"
}

Set-Content -LiteralPath $ConfigPath -Value $updated -Encoding ASCII

if (Test-Path -LiteralPath $StdoutPath) {
    Remove-Item -LiteralPath $StdoutPath -Force
}

if (Test-Path -LiteralPath $StderrPath) {
    Remove-Item -LiteralPath $StderrPath -Force
}

$process = Start-Process `
    -FilePath $ExePath `
    -ArgumentList '--loglevel', $AppLogLevel `
    -RedirectStandardOutput $StdoutPath `
    -RedirectStandardError $StderrPath `
    -PassThru

Start-Sleep -Seconds 3

[pscustomobject]@{
    ProcessId = $process.Id
    ConfigPath = $ConfigPath
    StdoutPath = $StdoutPath
    StderrPath = $StderrPath
    MqttTraceLevel = $MqttTraceLevel
    AppLogLevel = $AppLogLevel
} | Format-List
