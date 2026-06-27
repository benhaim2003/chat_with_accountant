# deploy.ps1 - deploys ca-cpa-bot (+ Redis sidecar) to Azure Container Apps
# Reads secrets from .env; run from the project root.
#
# WhatsApp activation is opt-in: if WHATSAPP_TOKEN / WHATSAPP_PHONE_NUMBER_ID /
# WHATSAPP_VERIFY_TOKEN are all present in .env, the adapter starts inside the
# container AND public HTTPS ingress is enabled on port 8080 so Meta can reach
# the /webhook/whatsapp endpoint. Without those keys, ingress stays off.

param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- Read .env -----------------------------------------------------------------
$envVars = @{}
# Read .env as UTF-8 explicitly. PowerShell 5.1's default is cp1252, which
# corrupts Hebrew names in PILOT_CLIENTS_JSON when they get re-encoded.
Get-Content "$PSScriptRoot\.env" -Encoding utf8 |
    Where-Object { $_ -notmatch '^\s*#' -and $_ -match '=' } |
    ForEach-Object {
        $parts = $_ -split '=', 2
        $key   = $parts[0].Trim()
        $value = $parts[1].Trim().Trim('"').Trim("'")
        $envVars[$key] = $value
    }

$required = @(
    'TELEGRAM_BOT_TOKEN','AZURE_SUBSCRIPTION_ID','AZURE_TENANT_ID','AZURE_CLIENT_ID',
    'AZURE_CLIENT_SECRET','EMAIL_USERNAME','SECRETARIAT_EMAIL','PILOT_CLIENTS_JSON'
)
foreach ($key in $required) {
    if (-not $envVars.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($envVars[$key])) {
        Write-Error ".env is missing required key: $key"
        exit 1
    }
}

$pollInterval = if ($envVars.ContainsKey('EMAIL_POLL_INTERVAL')) { $envVars['EMAIL_POLL_INTERVAL'] } else { '30' }
$logLevel     = if ($envVars.ContainsKey('LOG_LEVEL'))            { $envVars['LOG_LEVEL'] }            else { 'INFO' }

# --- WhatsApp (optional) -------------------------------------------------------
$whatsappKeys = @('WHATSAPP_TOKEN','WHATSAPP_PHONE_NUMBER_ID','WHATSAPP_VERIFY_TOKEN')
$whatsappEnabled = $true
foreach ($key in $whatsappKeys) {
    if (-not $envVars.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($envVars[$key])) {
        $whatsappEnabled = $false
        break
    }
}

if ($whatsappEnabled) {
    Write-Host "WhatsApp credentials found - enabling adapter + public ingress on :8080"
} else {
    Write-Host "WhatsApp credentials not found - Telegram-only deployment"
}

# --- ACR credentials -----------------------------------------------------------
Write-Host "Fetching ACR credentials..."
$acrPassword = az acr credential show --name remcpabotacr --query "passwords[0].value" -o tsv

# --- Image tag (commit hash busts Azure's :latest cache) -----------------------
$imageTag = (git rev-parse --short HEAD).Trim()
$imageName = "remcpabotacr.azurecr.io/cpa-bot:$imageTag"

# --- Optional WhatsApp YAML fragments -----------------------------------------
$whatsappSecrets = ""
$whatsappEnv     = ""
$ingressBlock    = ""
if ($whatsappEnabled) {
    $waToken   = $envVars['WHATSAPP_TOKEN']
    $waPhoneId = $envVars['WHATSAPP_PHONE_NUMBER_ID']
    $waVerify  = $envVars['WHATSAPP_VERIFY_TOKEN']
    $whatsappSecrets = @"

      - name: whatsapp-token
        value: "$waToken"
      - name: whatsapp-phone-number-id
        value: "$waPhoneId"
      - name: whatsapp-verify-token
        value: "$waVerify"
"@
    $whatsappEnv = @"

          - name: WHATSAPP_TOKEN
            secretRef: whatsapp-token
          - name: WHATSAPP_PHONE_NUMBER_ID
            secretRef: whatsapp-phone-number-id
          - name: WHATSAPP_VERIFY_TOKEN
            secretRef: whatsapp-verify-token
"@
    $ingressBlock = @"

    ingress:
      external: true
      targetPort: 8080
      transport: http
      allowInsecure: false
"@
}

# --- Build deployment YAML -----------------------------------------------------
$telegramToken    = $envVars['TELEGRAM_BOT_TOKEN']
$subscriptionId   = $envVars['AZURE_SUBSCRIPTION_ID']
$azureTenantId    = $envVars['AZURE_TENANT_ID']
$azureClientId    = $envVars['AZURE_CLIENT_ID']
$azureSecret      = $envVars['AZURE_CLIENT_SECRET']
$emailUsername    = $envVars['EMAIL_USERNAME']
$secretariatEmail = $envVars['SECRETARIAT_EMAIL']
# Base64-encode the pilot clients JSON so the deploy YAML stays ASCII-only —
# the Windows Azure CLI reads YAML as cp1252 and dies on Hebrew bytes otherwise.
$pilotClientsJson = $envVars['PILOT_CLIENTS_JSON']
$pilotClientsB64  = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($pilotClientsJson))

$yaml = @"
name: ca-cpa-bot
type: Microsoft.App/containerApps
location: northeurope
properties:
  managedEnvironmentId: /subscriptions/$subscriptionId/resourceGroups/rg-cpa-bot/providers/Microsoft.App/managedEnvironments/cae-cpa-bot
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
        value: "$telegramToken"
      - name: azure-tenant-id
        value: "$azureTenantId"
      - name: azure-client-id
        value: "$azureClientId"
      - name: azure-client-secret
        value: "$azureSecret"
      - name: secretariat-email
        value: "$secretariatEmail"
      - name: pilot-clients-json-b64
        value: "$pilotClientsB64"$whatsappSecrets$ingressBlock
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
            value: "$emailUsername"
          - name: SECRETARIAT_EMAIL
            secretRef: secretariat-email
          - name: REDIS_URL
            value: "redis://localhost:6379/0"
          - name: EMAIL_POLL_INTERVAL
            value: "$pollInterval"
          - name: LOG_LEVEL
            value: "$logLevel"
          - name: PILOT_CLIENTS_JSON_B64
            secretRef: pilot-clients-json-b64$whatsappEnv
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

if ($whatsappEnabled) {
    Write-Host ""
    Write-Host "WhatsApp webhook URL - paste this into Meta's dashboard:"
    $fqdn = az containerapp show -n ca-cpa-bot -g rg-cpa-bot --query "properties.configuration.ingress.fqdn" -o tsv
    Write-Host "  https://$fqdn/webhook/whatsapp"
    $verifyToken = $envVars['WHATSAPP_VERIFY_TOKEN']
    Write-Host "Verify token (same one you set in .env):"
    Write-Host "  $verifyToken"
}

Write-Host ""
Write-Host "Done. Check logs with:"
Write-Host "  az containerapp logs show -n ca-cpa-bot -g rg-cpa-bot --follow"
