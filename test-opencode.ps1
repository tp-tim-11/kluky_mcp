# test-opencode.ps1
# Standalone Windows test: load .env, inject custom provider into opencode.json,
# then launch OpenCode in the same directory as this script. Both .env and
# opencode.json must be siblings of this script. kluky_mcp is started
# automatically by OpenCode via the "mcp" block in opencode.json.
#
# Usage (from the directory where this script lives):
#   powershell -ExecutionPolicy Bypass -File .\test-opencode.ps1

$ErrorActionPreference = "Stop"

$RootDir    = $PSScriptRoot
$EnvFile    = Join-Path $RootDir ".env"
$ConfigFile = Join-Path $RootDir "opencode.json"

if (-not (Test-Path $EnvFile)) {
    Write-Error ".env not found at $EnvFile. Copy .env.example to .env first."
    exit 1
}
if (-not (Test-Path $ConfigFile)) {
    Write-Error "opencode.json not found at $ConfigFile."
    exit 1
}

# --- Load .env into a hashtable and into the current process env ---
Write-Host "Loading .env..."
$envVars = @{}
Get-Content $EnvFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -eq "" -or $line.StartsWith("#")) { return }
    $eq = $line.IndexOf("=")
    if ($eq -lt 1) { return }
    $key = $line.Substring(0, $eq).Trim()
    $val = $line.Substring($eq + 1).Trim()
    # Strip surrounding quotes if present
    if (($val.StartsWith('"') -and $val.EndsWith('"')) -or
        ($val.StartsWith("'") -and $val.EndsWith("'"))) {
        $val = $val.Substring(1, $val.Length - 2)
    }
    $envVars[$key] = $val
    Set-Item -Path "Env:$key" -Value $val
}

$baseUrl = $envVars["OPENCODE_PROVIDER_BASE_URL"]
$models  = $envVars["OPENCODE_PROVIDER_MODELS"]
$apiKey  = $envVars["OPENCODE_PROVIDER_API_KEY"]

# --- Inject custom provider if configured ---
if ([string]::IsNullOrWhiteSpace($baseUrl)) {
    Write-Host "OPENCODE_PROVIDER_BASE_URL is empty; leaving opencode.json untouched."
    Write-Host "You can run /connect inside the OpenCode TUI instead."
} else {
    if ([string]::IsNullOrWhiteSpace($models)) {
        Write-Error "OPENCODE_PROVIDER_BASE_URL is set but OPENCODE_PROVIDER_MODELS is empty."
        exit 1
    }
    if ([string]::IsNullOrWhiteSpace($apiKey)) {
        Write-Error "OPENCODE_PROVIDER_BASE_URL is set but OPENCODE_PROVIDER_API_KEY is empty."
        exit 1
    }

    $modelList = @($models.Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" })
    if ($modelList.Count -eq 0) {
        Write-Error "OPENCODE_PROVIDER_MODELS contains no valid model IDs."
        exit 1
    }

    Write-Host "Injecting custom provider into opencode.json..."
    $config = Get-Content $ConfigFile -Raw | ConvertFrom-Json

    # Ensure "provider" key exists on the root object
    if (-not ($config.PSObject.Properties.Name -contains "provider")) {
        $config | Add-Member -NotePropertyName "provider" -NotePropertyValue ([pscustomobject]@{}) -Force
    }

    # Build the models object
    $modelsObj = [pscustomobject]@{}
    foreach ($m in $modelList) {
        $modelsObj | Add-Member -NotePropertyName $m -NotePropertyValue ([pscustomobject]@{ name = $m }) -Force
    }

    $providerObj = [pscustomobject]@{
        npm     = "@ai-sdk/openai-compatible"
        name    = "My Custom Provider"
        options = [pscustomobject]@{
            baseURL = $baseUrl
            apiKey  = $apiKey
        }
        models  = $modelsObj
    }

    # Add/overwrite "my-custom-provider" under "provider"
    $config.provider | Add-Member -NotePropertyName "my-custom-provider" -NotePropertyValue $providerObj -Force

    # Pre-select the first model so /connect is not needed
    $defaultModel = "my-custom-provider/$($modelList[0])"
    $config | Add-Member -NotePropertyName "model" -NotePropertyValue $defaultModel -Force

    # Serialize once, sanity-check, then write atomically
    $json = $config | ConvertTo-Json -Depth 32
    try {
        $null = $json | ConvertFrom-Json
    } catch {
        Write-Error "Refusing to write: produced JSON failed re-parse. $_"
        exit 1
    }

    $tempFile = "$ConfigFile.tmp"
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($tempFile, $json, $utf8NoBom)
    Move-Item -Path $tempFile -Destination $ConfigFile -Force

    # Verify final on-disk file parses cleanly
    try {
        $null = Get-Content $ConfigFile -Raw | ConvertFrom-Json
    } catch {
        Write-Error "Post-write verification failed. $_"
        exit 1
    }

    Write-Host "Provider 'my-custom-provider' written. Default model: $defaultModel"
}

# --- Launch OpenCode (kluky_mcp auto-starts via opencode.json mcp block) ---
Write-Host ""
Write-Host "Starting OpenCode in $RootDir..."
Write-Host "kluky_mcp will be launched automatically by OpenCode via the 'mcp' block."
Write-Host "Press Ctrl+C in the OpenCode TUI to exit."
Write-Host ""

Push-Location $RootDir
try {
    & opencode --port 4096
} finally {
    Pop-Location
}
