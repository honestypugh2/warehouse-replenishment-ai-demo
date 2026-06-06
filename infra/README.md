# Infrastructure (`infra/`)

Azure infrastructure for the **AI Warehouse Replenishment Orchestration Demo**,
provisioned with the [Azure Developer CLI (`azd`)](https://learn.microsoft.com/azure/developer/azure-developer-cli/).

> **Scope:** Databricks and D365 are **always mocked** in this demo (they read the
> JSON data pack in [`../data`](../data)). This infrastructure exists only to
> light up the **live Foundry** reasoning path (`FOUNDRY_MODE=live`). The mock
> demo needs no Azure resources at all.

## What gets deployed

| Resource | Type | Purpose |
| --- | --- | --- |
| Microsoft Foundry account | `Microsoft.CognitiveServices/accounts` (`AIServices`) | Hosts the project + model |
| Foundry project | `Microsoft.CognitiveServices/accounts/projects` | Project endpoint the backend calls |
| Model deployment | `Microsoft.CognitiveServices/accounts/deployments` | `gpt-4o` for the reasoner |
| Log Analytics workspace | `Microsoft.OperationalInsights/workspaces` | Audit + OTel GenAI traces |
| Key Vault | `Microsoft.KeyVault/vaults` | Secrets store (RBAC auth) for when Databricks/D365 go live |
| User-assigned managed identity | `Microsoft.ManagedIdentity/userAssignedIdentities` | Least-privilege identity for the app when hosted on Azure |
| Role assignments | `Microsoft.Authorization/roleAssignments` | **Foundry User** for the app MI, the project MI, and you |

All resource types pin the **latest stable API versions**.

### Files

| File | Role |
| --- | --- |
| [main.bicep](main.bicep) | azd entry point (subscription scope). Creates the resource group + deploys the module. |
| [bicep/main.bicep](bicep/main.bicep) | The resources module (resource-group scope). |
| [main.parameters.json](main.parameters.json) | Maps azd environment variables to Bicep parameters. |
| [../azure.yaml](../azure.yaml) | azd project definition (points azd at `infra/main.bicep`). |

## RBAC — Foundry User (least privilege)

The backend authenticates with `DefaultAzureCredential`: the user-assigned managed
identity when hosted on Azure, or your signed-in `az` account locally. Both, plus
the project's own managed identity, are granted the **Foundry User** role
(`53ca6127-db72-4b80-b1b0-d745d6d5456d`) on the Foundry account — the
least-privilege role that allows running inference against the project's model
deployment.

> The Foundry RBAC roles were recently renamed (Foundry User was previously
> *Azure AI User*). We assign by **role definition GUID** so the rename rollout
> doesn't break the template.
>
> Per Microsoft guidance, we deliberately **do not** use `Cognitive Services *`
> or `Azure AI Developer` roles — they don't apply to Foundry projects. See
> [RBAC for Microsoft Foundry](https://learn.microsoft.com/azure/foundry/concepts/rbac-foundry).

## Deployment tiers — dev / demo / prod

A single `deploymentTier` parameter sizes the deployment. **`demo` is the default
and is enough to run this demo.**

| Setting | `dev` | `demo` (default) | `prod` |
| --- | --- | --- | --- |
| Log Analytics retention (days) | 30 | 30 | 90 |
| Model capacity (K TPM) | 10 | 30 | 50 |
| Key Vault purge protection | off | off | **on** |
| Foundry local-auth (account keys) | enabled | enabled | **disabled (Entra-only)** |

Select a tier with:

```bash
azd env set DEPLOYMENT_TIER prod   # dev | demo | prod
```

## Provision with azd

### Prerequisites

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) `2.67.0+`
- [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) (`azd`)
- A role that can create resources **and** assign roles (e.g. **Owner** on the
  subscription or resource group). Assigning the Foundry User role requires
  role-assignment permission.

### Steps

```bash
# from the repository root
az login
azd auth login

# create an azd environment (names the resource group rg-<name>)
azd env new replen-demo

# choose a region and (optionally) a tier
azd env set AZURE_LOCATION eastus2
azd env set DEPLOYMENT_TIER demo      # default; omit for demo

# provision everything
azd provision
```

`azd` discovers your object ID automatically and grants you Foundry User, so you
can call the project locally right after provisioning.

### Wire the backend to live Foundry

`azd` writes the deployment outputs to `.azure/<env>/.env`. Copy these into the
backend `.env` (see [../.env.example](../.env.example)):

```bash
AZURE_FOUNDRY_PROJECT_ENDPOINT   # -> AZURE_FOUNDRY_PROJECT_ENDPOINT
AZURE_FOUNDRY_MODEL_DEPLOYMENT   # -> AZURE_FOUNDRY_MODEL_DEPLOYMENT (gpt-4o)
AZURE_TENANT_ID                  # -> AZURE_TENANT_ID
```

Then run the app in live mode:

```bash
./start.sh --live
```

### Inspect or tear down

```bash
azd show          # view provisioned resources + endpoints
azd down --purge  # delete the resource group (and purge soft-deleted resources)
```

## Without azd (plain Azure CLI)

```bash
az group create -n rg-replen-demo -l eastus2
az deployment group create \
  -g rg-replen-demo \
  -f infra/bicep/main.bicep \
  -p deploymentTier=demo \
     principalId="$(az ad signed-in-user show --query id -o tsv)"
```

## Related

- [databricks/](databricks/) — notes for wiring a real Databricks SQL Warehouse.
- [github-actions/](github-actions/) — CI workflow notes.
