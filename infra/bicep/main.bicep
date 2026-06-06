// main.bicep — resource module for the replenishment orchestration demo.
//
// Provisions the supporting Azure resources for the live Foundry path:
//   - Microsoft Foundry (Azure AI Foundry) account + project + model deployment
//   - Log Analytics workspace (audit + OTel GenAI traces)
//   - Application Insights + a Foundry project connection (lights up the portal
//     Tracing + Monitoring tabs for agent runs and GenAI model calls)
//   - Key Vault (D365 / Databricks secrets — used only when those are wired live)
//   - User-assigned managed identity (least-privilege agent identity)
//   - Foundry User role assignments (Entra-only auth) for the app identity, the
//     project identity, and the signed-in developer.
//
// Deployed as a module from infra/main.bicep (subscription scope). The default
// `demo` tier is sized to support this demo. Review networking and Purview
// before production.

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Short, lowercase name prefix used for resource names.')
@minLength(3)
@maxLength(11)
param namePrefix string = 'replen'

@description('Deployment tier. Tunes SKUs, retention, and hardening. The default (demo) is sized for this demo.')
@allowed([
  'dev'
  'demo'
  'prod'
])
param deploymentTier string = 'demo'

@description('Foundry model deployment name.')
param modelDeploymentName string = 'gpt-4o'

@description('Model name to deploy.')
param modelName string = 'gpt-4o'

@description('Model version to deploy.')
param modelVersion string = '2024-08-06'

@description('Object ID of the developer/principal that calls Foundry locally (az ad signed-in-user show --query id -o tsv). Leave empty to skip the developer role assignment.')
param principalId string = ''

@description('Tags applied to every resource.')
param tags object = {}

// Per-tier configuration. The demo defaults are intentionally modest so the
// default deployment is enough to run the demo without quota friction.
var tierConfig = {
  dev: {
    logRetentionDays: 30
    modelCapacity: 10
    kvPurgeProtection: false
    disableLocalAuth: false
  }
  demo: {
    logRetentionDays: 30
    modelCapacity: 30
    kvPurgeProtection: false
    disableLocalAuth: false
  }
  prod: {
    logRetentionDays: 90
    modelCapacity: 50
    kvPurgeProtection: true
    disableLocalAuth: true
  }
}
var cfg = tierConfig[deploymentTier]

var suffix = uniqueString(resourceGroup().id)
var foundryName = '${namePrefix}-foundry-${suffix}'
var projectName = '${namePrefix}-project'
var lawName = '${namePrefix}-law-${suffix}'
var appiName = '${namePrefix}-appi-${suffix}'
var kvName = '${namePrefix}kv${take(suffix, 8)}'
var miName = '${namePrefix}-mi-${suffix}'

// Foundry built-in role. Use the role definition GUID (not the name) because the
// Foundry roles were recently renamed (Foundry User was previously "Azure AI
// User"). Foundry User is the least-privilege role for running inference against
// a project's model deployments.
//
// Do NOT use `Cognitive Services *` or `Azure AI Developer` roles for Foundry —
// per Microsoft guidance they don't apply to Foundry projects / hosted agents.
// https://learn.microsoft.com/azure/foundry/concepts/rbac-foundry
var foundryUserRoleId = '53ca6127-db72-4b80-b1b0-d745d6d5456d'

resource law 'Microsoft.OperationalInsights/workspaces@2025-07-01' = {
  name: lawName
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: cfg.logRetentionDays
  }
}

// Workspace-based Application Insights. Foundry routes agent-run and GenAI
// (OpenTelemetry) traces here; the backend also exports OTel spans to it via
// the connection string (see src/foundry/observability.py).
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appiName
  location: location
  kind: 'web'
  tags: tags
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: law.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

resource mi 'Microsoft.ManagedIdentity/userAssignedIdentities@2024-11-30' = {
  name: miName
  location: location
  tags: tags
}

resource kv 'Microsoft.KeyVault/vaults@2025-05-01' = {
  name: kvName
  location: location
  tags: tags
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    enablePurgeProtection: cfg.kvPurgeProtection ? true : null
    publicNetworkAccess: 'Enabled'
  }
}

resource foundry 'Microsoft.CognitiveServices/accounts@2026-03-01' = {
  name: foundryName
  location: location
  tags: tags
  kind: 'AIServices'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    allowProjectManagement: true
    customSubDomainName: foundryName
    publicNetworkAccess: 'Enabled'
    // prod uses Entra-only auth (no account keys); dev/demo keep keys for convenience.
    disableLocalAuth: cfg.disableLocalAuth
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2026-03-01' = {
  parent: foundry
  name: projectName
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {}
}

resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2026-03-01' = {
  parent: foundry
  name: modelDeploymentName
  sku: { name: 'GlobalStandard', capacity: cfg.modelCapacity }
  properties: {
    model: { format: 'OpenAI', name: modelName, version: modelVersion }
  }
}

// Foundry project connection to Application Insights. This is what makes the
// portal's Tracing and Monitoring tabs (per project) show agent runs and model
// telemetry. The connection stores the App Insights connection string as an
// ApiKey credential.
resource appInsightsConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2026-03-01' = {
  parent: project
  name: 'appinsights'
  properties: {
    category: 'AppInsights'
    target: appInsights.id
    authType: 'ApiKey'
    isSharedToAll: true
    credentials: {
      key: appInsights.properties.ConnectionString
    }
    metadata: {
      ApiType: 'Azure'
      ResourceId: appInsights.id
    }
  }
}

// --- RBAC: Entra-only access to run Foundry inference (least privilege) ---
// The backend authenticates with DefaultAzureCredential: the user-assigned MI in
// Azure, or the signed-in developer locally. Foundry User on the account scope
// grants the data-plane permission to call the project's model deployment.

resource miFoundryUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundry.id, mi.id, foundryUserRoleId)
  scope: foundry
  properties: {
    principalId: mi.properties.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', foundryUserRoleId)
    principalType: 'ServicePrincipal'
  }
}

resource projectFoundryUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundry.id, project.id, foundryUserRoleId)
  scope: foundry
  properties: {
    principalId: project.identity.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', foundryUserRoleId)
    principalType: 'ServicePrincipal'
  }
}

resource userFoundryUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(foundry.id, principalId, foundryUserRoleId)
  scope: foundry
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', foundryUserRoleId)
    principalType: 'User'
  }
}

output foundryEndpoint string = foundry.properties.endpoint
// Use this value for AZURE_FOUNDRY_PROJECT_ENDPOINT in the backend .env.
output foundryProjectEndpoint string = 'https://${foundryName}.services.ai.azure.com/api/projects/${projectName}'
output foundryAccountName string = foundry.name
output modelDeploymentName string = modelDeployment.name
output projectName string = project.name
output logAnalyticsId string = law.id
output applicationInsightsConnectionString string = appInsights.properties.ConnectionString
output applicationInsightsName string = appInsights.name
output keyVaultUri string = kv.properties.vaultUri
output managedIdentityClientId string = mi.properties.clientId
