// main.bicep — azd entry point (subscription scope).
//
// Creates the resource group and deploys the demo resources module under it.
// azd populates `environmentName`, `location`, and `principalId` automatically.
//
// Provision with:  azd provision   (or `azd up`)

targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the azd environment. Names the resource group and tags all resources.')
param environmentName string

@minLength(1)
@description('Primary Azure region for all resources.')
param location string

@description('Deployment tier: dev, demo, or prod. The default (demo) is sized for this demo.')
@allowed([
  'dev'
  'demo'
  'prod'
])
param deploymentTier string = 'demo'

@description('Object ID of the signed-in user/principal for local Foundry access. azd populates this automatically.')
param principalId string = ''

@description('Foundry model deployment name.')
param modelDeploymentName string = 'gpt-4o'

var tags = {
  'azd-env-name': environmentName
  workload: 'warehouse-replenishment-demo'
  tier: deploymentTier
}

resource rg 'Microsoft.Resources/resourceGroups@2025-04-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: tags
}

module resources 'bicep/main.bicep' = {
  name: 'replen-resources'
  scope: rg
  params: {
    location: location
    deploymentTier: deploymentTier
    modelDeploymentName: modelDeploymentName
    principalId: principalId
    tags: tags
  }
}

// Outputs are written to the azd environment (.azure/<env>/.env) and map directly
// to the backend's expected variable names.
output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_RESOURCE_GROUP string = rg.name
output AZURE_FOUNDRY_PROJECT_ENDPOINT string = resources.outputs.foundryProjectEndpoint
output AZURE_FOUNDRY_MODEL_DEPLOYMENT string = resources.outputs.modelDeploymentName
output AZURE_KEY_VAULT_URI string = resources.outputs.keyVaultUri
output AZURE_LOG_ANALYTICS_ID string = resources.outputs.logAnalyticsId
output APPLICATIONINSIGHTS_CONNECTION_STRING string = resources.outputs.applicationInsightsConnectionString
output FOUNDRY_MODE string = 'live'
output FOUNDRY_USE_AGENTS string = 'true'
