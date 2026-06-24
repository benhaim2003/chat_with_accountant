# deploy.ps1 — deploys ca-cpa-bot (+ Redis sidecar) to Azure Container Apps
# Reads secrets from .env; run from the project root.

param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- Read .env -----------------------------------------------------------------
$envVars = @{}
Get-Content "$PSScriptRoot\.env" |
    Where-Object { $_ -notmatch '^\s*#' -and $_ -match '=' } |
    ForEach-Object {
        $parts = $_ -split '=', 2
        $key   = $parts[0].Trim()
        $value = $parts[1].Trim().Trim('"').Trim("'")
        $envVars[$key] = $value
    }

$required = @(
    'TELEGRAM_BOT_TOKEN','AZURE_TENANT_ID','AZURE_CLIENT_ID',
    'AZURE_CLIENT_SECRET','EMAIL_USERNAME','SECRETARIAT_EMAIL'
)
foreach ($key in $required) {
    if (-not $envVars.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($envVars[$key])) {
        Write-Error ".env is missing required key: $key"
        exit 1
    }
}

$pollInterval = if ($envVars.ContainsKey('EMAIL_POLL_INTERVAL')) { $envVars['EMAIL_POLL_INTERVAL'] } else { '30' }
$logLevel     = if ($envVars.ContainsKey('LOG_LEVEL'))            { $envVars['LOG_LEVEL'] }            else { 'INFO' }

# --- ACR credentials -----------------------------------------------------------
Write-Host "Fetching ACR credentials..."
$acrPassword = az acr credential show --name remcpabotacr --query "passwords[0].value" -o tsv

# --- Image tag (commit hash busts Azure's :latest cache) -----------------------
$imageTag = (git rev-parse --short HEAD).Trim()
$imageName = "remcpabotacr.azurecr.io/cpa-bot:$imageTag"

# --- Build deployment YAML -----------------------------------------------------
$yaml = @"
name: ca-cpa-bot
type: Microsoft.App/containerApps
location: northeurope
properties:
  managedEnvironmentId: /subscriptions/[REDACTED-SUBSCRIPTION]/resourceGroups/rg-cpa-bot/providers/Microsoft.App/managedEnvironments/cae-cpa-bot
  configuration:
    activeRevisionsMode: Single
    registries:
      - server: remcpabotacr.azurecr.io
        username: remcpabotacr
        passwordSecretRef: acr-password
    secrets:
      - name: acr-password
        value: "$acrPassword"
      - name: telegram-token
        value: "$($envVars['TELEGRAM_BOT_TOKEN'])"
      - name: azure-tenant-id
        value: "$($envVars['AZURE_TENANT_ID'])"
      - name: azure-client-id
        value: "$($envVars['AZURE_CLIENT_ID'])"
      - name: azure-client-secret
        value: "$($envVars['AZURE_CLIENT_SECRET'])"
      - name: secretariat-email
        value: "$($envVars['SECRETARIAT_EMAIL'])"
  template:
    containers:
      - name: ca-cpa-bot
        image: $imageName
        resources:
          cpu: 0.5
          memory: 1Gi
        env:
          - name: TELEGRAM_BOT_TOKEN
            secretRef: telegram-token
          - name: AZURE_TENANT_ID
            secretRef: azure-tenant-id
          - name: AZURE_CLIENT_ID
            secretRef: azure-client-id
          - name: AZURE_CLIENT_SECRET
            secretRef: azure-client-secret
          - name: EMAIL_USERNAME
            value: "$($envVars['EMAIL_USERNAME'])"
          - name: SECRETARIAT_EMAIL
            secretRef: secretariat-email
          - name: REDIS_URL
            value: "redis://localhost:6379/0"
          - name: EMAIL_POLL_INTERVAL
            value: "$pollInterval"
          - name: LOG_LEVEL
            value: "$logLevel"
      - name: redis
        image: redis:7-alpine
        resources:
          cpu: 0.25
          memory: 0.5Gi
    scale:
      minReplicas: 1
      maxReplicas: 1
"@

$yamlPath = "$PSScriptRoot\deploy-update.yaml"
$yaml | Set-Content $yamlPath -Encoding utf8

# --- Deploy --------------------------------------------------------------------
Write-Host "Deploying ca-cpa-bot with Redis sidecar..."
az containerapp update `
    --name ca-cpa-bot `
    --resource-group rg-cpa-bot `
    --yaml $yamlPath

Remove-Item $yamlPath -Force

Write-Host "Done. Check logs with:"
Write-Host "  az containerapp logs show -n ca-cpa-bot -g rg-cpa-bot --follow"
