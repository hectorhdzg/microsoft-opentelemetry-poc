# A365 Agent Setup Guide

End-to-end walkthrough for deploying a Python Agent Framework agent to Azure,
publishing it to M365, and making it available in Teams / Copilot.

> **Status (March 2026):** Blueprint created via CLI (`otel-poc Blueprint`,
> app ID `1b4b1b62-4e1e-4643-bd66-6c3c7cc27809`). Manifest published via
> `a365 publish`. Pending: bot endpoint registration, deployment, and Teams activation.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Blueprint Setup](#2-blueprint-setup)
3. [Service Principal & Credentials](#3-service-principal--credentials)
4. [Permissions & Consent](#4-permissions--consent)
5. [Azure Deployment](#5-azure-deployment)
6. [Bot Endpoint Registration](#6-bot-endpoint-registration)
7. [Manifest & Admin Center](#7-manifest--admin-center)
8. [Publishing & Activation](#8-publishing--activation)
9. [Observability & Telemetry](#9-observability--telemetry)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Prerequisites

| Component | Details |
|-----------|---------|
| Python | 3.11+ (Azure uses 3.11.x, local can be 3.12) |
| A365 CLI | `dotnet tool install -g Microsoft.Agents.A365.DevTools.Cli` — v1.1.115-preview used here |
| Azure CLI | `az` — for resource management |
| UV | Python package manager — needed for Azure deployment |
| Tenant | A365-enabled test tenant (e.g. `a365preview070.onmicrosoft.com`) |
| Azure OpenAI | Endpoint + deployment (e.g. `gpt-4.1`) with API key |

### SDK Versions (Pinned)

```toml
agent-framework-azure-ai==1.0.0b251218
agent-framework-core==1.0.0b251218
```

These are pre-release builds. The `microsoft_agents_a365_*` packages are also
pre-release (pulled via `prerelease = "allow"` in `pyproject.toml`).

---

## 2. Blueprint Setup

The **blueprint** is the Entra ID app registration that represents your agent.

### Option A: Via A365 CLI (recommended)

```bash
a365 setup blueprint
```

This creates the blueprint app, service principal, client secret, federated identity
credential (FIC), and registers the bot messaging endpoint — all in one step.

**Known issue:** WAM (Windows Account Manager) authentication does not work inside
VS Code's integrated terminal. You must run this in an **external PowerShell window**:

```powershell
# From VS Code terminal, open an external window:
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'"
# Then run in that window:
a365 setup blueprint
```

### Option B: Via Developer Portal + manual steps

If the CLI fails or you need more control:

1. Go to [Developer Portal](https://dev.teams.microsoft.com) → Tools → Bot management
2. Create a new bot → this creates the Entra app registration (the blueprint)
3. Note the **App ID** — this is your blueprint ID
4. Manually create the service principal, client secret, and FIC (see next section)

### What we used

- Blueprint App ID: `1b4b1b62-4e1e-4643-bd66-6c3c7cc27809`
- Blueprint display name: `otel-poc Blueprint`
- Created via: `a365 setup blueprint --no-endpoint` (external PowerShell)

---

## 3. Service Principal & Credentials

If the CLI didn't create these (e.g. you used Developer Portal), do it manually:

### Create service principal

```bash
az ad sp create --id <blueprint-app-id>
```

Note the `id` field in the output — this is the **SP Object ID**.

### Create client secret

```bash
az ad app credential reset \
  --id <blueprint-app-id> \
  --display-name "A365 Agent Secret" \
  --years 1
```

Save the `password` — this is your `CLIENT_SECRET`.

### Create federated identity credential (FIC)

```bash
az ad app federated-credential create \
  --id <blueprint-app-id> \
  --parameters '{
    "name": "A365AgentFIC",
    "issuer": "https://login.microsoftonline.com/<tenant-id>/v2.0",
    "subject": "<sp-object-id>",
    "audiences": ["api://<blueprint-app-id>"],
    "description": "FIC for A365 agent"
  }'
```

### What we used

- SP Object ID: `744c774e-69fb-4019-a0cf-7d244bc9d0a0`
- Client secret: managed by the CLI (stored encrypted in `a365.generated.config.json`)
- FIC: created automatically by `a365 setup blueprint`

---

## 4. Permissions & Consent

The blueprint needs permissions to several A365 APIs. The CLI handles this via:

```bash
a365 setup permissions mcp    # MCP server permissions (Mail, etc.)
a365 setup permissions bot    # Bot messaging + observability permissions
```

### Required API permissions (application type)

| API | Scopes |
|-----|--------|
| Microsoft Graph | `Mail.ReadWrite`, `Mail.Send`, `Chat.ReadWrite`, `User.Read.All`, `Sites.Read.All` |
| Agent 365 Tools | `McpServers.Mail.All`, `McpServersMetadata.Read.All` |
| Messaging Bot API (`5a807f24-...`) | `Authorization.ReadWrite`, `user_impersonation` |
| Observability API (`9b975845-...`) | `user_impersonation` |
| Power Platform API (`8578e004-...`) | `Connectivity.Connections.Read` |

All must have **admin consent granted**. The CLI does this automatically.

You can verify in Entra ID → App registrations → your blueprint → API permissions.

---

## 5. Azure Deployment

### Infrastructure setup

```bash
# Create resource group (if needed)
az group create --name rg-hectorh --location westus2

# Create app service plan
az appservice plan create \
  --name rg-hectorh-plan \
  --resource-group rg-hectorh \
  --sku B1 \
  --is-linux

# Create web app
az webapp create \
  --name otel-observability-poc-webapp \
  --resource-group rg-hectorh \
  --plan rg-hectorh-plan \
  --runtime "PYTHON:3.11"
```

### App Settings

These must be set on the Azure Web App (via portal or CLI):

```bash
az webapp config appsettings set --name otel-observability-poc-webapp \
  --resource-group rg-hectorh --settings \
  "AZURE_OPENAI_API_KEY=<key>" \
  "AZURE_OPENAI_ENDPOINT=https://<name>.openai.azure.com/" \
  "AZURE_OPENAI_DEPLOYMENT=gpt-4.1" \
  "AZURE_OPENAI_API_VERSION=2024-12-01-preview" \
  "PORT=3978" \
  "WEBSITES_PORT=3978" \
  "AUTH_HANDLER_NAME=AGENTIC" \
  "REQUIRE_AUTH_ON_ROUTES=false" \
  "CLIENT_ID=<blueprint-app-id>" \
  "CLIENT_SECRET=<client-secret>" \
  "TENANT_ID=<tenant-id>" \
  "AGENT_ID=<blueprint-app-id>" \
  "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID=<blueprint-app-id>" \
  "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET=<client-secret>" \
  "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID=<tenant-id>" \
  "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__SCOPES=5a807f24-c9de-44ee-a3a7-329e88a00ffc/.default" \
  "CONNECTIONSMAP_0_SERVICEURL=*" \
  "CONNECTIONSMAP_0_CONNECTION=SERVICE_CONNECTION" \
  "AGENTAPPLICATION__USERAUTHORIZATION__HANDLERS__AGENTIC__SETTINGS__TYPE=AgenticUserAuthorization" \
  "AGENTAPPLICATION__USERAUTHORIZATION__HANDLERS__AGENTIC__SETTINGS__NAME=AGENTIC" \
  "AGENTAPPLICATION__USERAUTHORIZATION__HANDLERS__AGENTIC__SETTINGS__SCOPES=5a807f24-c9de-44ee-a3a7-329e88a00ffc/.default" \
  "AGENTAPPLICATION__USERAUTHORIZATION__HANDLERS__AGENTIC__SETTINGS__ALT_BLUEPRINT_NAME=SERVICE_CONNECTION" \
  "ENABLE_OBSERVABILITY=true" \
  "ENABLE_A365_EXPORTER=true" \
  "ENABLE_A365_OBSERVABILITY_EXPORTER=true" \
  "ENABLE_OTEL=true" \
  "ENABLE_INSTRUMENTATION=true" \
  "ENABLE_SENSITIVE_DATA=true" \
  "OBSERVABILITY_SERVICE_NAME=agent-framework-sample" \
  "OBSERVABILITY_SERVICE_NAMESPACE=agent-framework.samples" \
  "LOG_LEVEL=INFO"
```

### Deploy the code

```bash
a365 deploy
```

Or manually via zip deploy:

```bash
az webapp deploy --name otel-observability-poc-webapp \
  --resource-group rg-hectorh \
  --src-path <zip-file> \
  --type zip
```

### Critical: Server must bind to 0.0.0.0

The `host_agent_server.py` detects Azure via `WEBSITE_INSTANCE_ID` env var and binds
to `0.0.0.0` instead of `localhost`. Without this, health probes and incoming messages
fail because Azure's reverse proxy can't reach the app.

```python
is_azure = environ.get("WEBSITE_INSTANCE_ID") is not None
bind_host = "0.0.0.0" if is_azure else "localhost"
```

### Verify deployment

```bash
# Health check
curl https://otel-observability-poc-webapp.azurewebsites.net/api/health

# Messaging endpoint (should return 401/auth error, NOT 404)
curl https://otel-observability-poc-webapp.azurewebsites.net/api/messages
# Expected: {"error": "Authorization header not found"}
```

---

## 6. Bot Endpoint Registration

**This is the step that blocked us for 2 days.**

The A365 service needs to know where to send messages to your agent. This is done
via `a365 setup blueprint`, specifically the endpoint registration part. Without it,
`botId`, `botMsaAppId`, and `botMessagingEndpoint` remain `null` in
`a365.generated.config.json` and the agent **never receives any messages**.

### How to register the endpoint

```bash
# Must run in EXTERNAL PowerShell (not VS Code terminal) due to WAM auth
a365 setup blueprint --endpoint-only
```

This registers:
- **Endpoint Name:** `<webAppName>-endpoint`
- **Messaging Endpoint:** `https://<webAppName>.azurewebsites.net/api/messages`
- **Region:** as configured in `a365.config.json`
- **Blueprint ID:** from `a365.generated.config.json`

### Verify registration

Check `a365.generated.config.json`:

```json
{
  "agentBlueprintId": "1b4b1b62-4e1e-4643-bd66-6c3c7cc27809",
  "botId": "1b4b1b62-...",        // was null
  "botMsaAppId": "1b4b1b62-...",   // was null
  "botMessagingEndpoint": "https://...azurewebsites.net/api/messages",  // was null
  "completed": true                                          // was false
}
```

### Do NOT create an Azure Bot Service resource

Standard `az bot create` creates a generic Azure Bot Service resource — this is
**not the same** as the A365 bot endpoint registration and will actually **conflict**
with it (causes `InternalServerError` when A365 tries to create its own). If you
accidentally created one, delete it before running the CLI:

```bash
az bot delete --name <bot-name> --resource-group <rg>
```

---

## 7. Manifest & Admin Center

### Manifest structure

The manifest is generated by `a365 publish`. It uses the `vdevPreview` schema with
`agenticUserTemplates` — the simplified format that doesn't require `bots` or
`copilotAgents` sections.

```json
{
  "$schema": ".../teams/vdevPreview/MicrosoftTeams.schema.json",
  "id": "<blueprint-app-id>",
  "manifestVersion": "devPreview",
  "version": "1.0.0",
  "agenticUserTemplates": [
    {
      "id": "<template-id>",
      "file": "agenticUserTemplateManifest.json"
    }
  ]
}
```

The `agenticUserTemplateManifest.json` links the template to the blueprint:

```json
{
  "id": "<template-id>",
  "schemaVersion": "0.1.0-preview",
  "agentIdentityBlueprintId": "<blueprint-app-id>",
  "communicationProtocol": "activityProtocol"
}
```

Key points:
- **`agenticUserTemplates`** — the only required section (no `bots` or `copilotAgents` needed)
- **`manifestVersion: "devPreview"`** — required
- **Use `a365 publish`** to generate the manifest zip — it updates IDs from the config automatically
- The `name.short` field must be ≤30 characters

### Generate and upload

1. Run `a365 publish` — this updates IDs in `manifest/manifest.json` and creates `manifest/manifest.zip`
2. Go to [M365 Admin Center](https://admin.microsoft.com) → Agents → All agents
3. Click **Upload custom agent**
4. Upload `manifest/manifest.zip`

### Activate the app

1. In admin center, find your app → **Status** column
2. Click to set availability: **Deployed: All users**
3. Verify channels show: **Copilot + Teams**

---

## 8. Publishing & Activation

### Publish to Titles (via CLI)

```bash
a365 publish
```

This creates a Title ID (e.g. `T_40c120b2-f2f4-44b8-65b5-9b656a5c9242`) which
represents your agent in the M365 app catalog.

### Allow users (optional)

```bash
a365 allow-users --all
```

Note: This returned HTTP 500 in our case — the admin center manual activation
(step above) is the workaround.

### Developer Portal configuration

Go to [Developer Portal](https://dev.teams.microsoft.com) → Apps → your agent:
- **Agent Type:** Bot Based
- **Bot ID:** your blueprint app ID
- No messaging endpoint field here — that's handled by the A365 endpoint registration

---

## 9. Observability & Telemetry

### Three telemetry destinations

1. **Admin Center → Agent → Activity tab** — sessions, triggers, actions
2. **Purview AI Observability** — security/compliance view, agent inventory
3. **Console/Application logs** — standard Python logging

### OpenTelemetry span types

| Span | What it captures |
|------|-----------------|
| `InvokeAgent` | Full agent invocation lifecycle |
| `ExecuteTool` | Individual MCP tool calls |
| `Inference` | LLM inference calls |

### Required env vars for telemetry

```env
ENABLE_OBSERVABILITY=true
ENABLE_A365_EXPORTER=true
ENABLE_A365_OBSERVABILITY_EXPORTER=true
ENABLE_OTEL=true
ENABLE_INSTRUMENTATION=true
AUTH_HANDLER_NAME=AGENTIC
```

### How it works

```
Agent code → OpenTelemetry SDK → A365 Exporter → A365 Observability API → Admin Center / Purview
```

The `microsoft_distro_observability_config.py` calls `configure_microsoft_opentelemetry()`
which sets up the A365 trace exporter and AgentFramework auto-instrumentation.

The observability token is acquired via SSO token exchange (when a real user is
chatting via Teams) or via client credentials fallback (S2S).

---

## 10. Troubleshooting

### Agent doesn't appear in Teams Agent Store

- Verify `a365.generated.config.json` shows `botId` ≠ null and `completed: true`
- Verify manifest was generated via `a365 publish` with correct blueprint ID
- Verify admin center shows the app as "Deployed: All users"
- Wait 10-15 minutes after endpoint registration for propagation
- Clear Teams cache or try Teams web client

### WAM authentication fails in VS Code terminal

**Symptom:** `a365 setup blueprint` hangs at "Authenticating via Windows Account Manager..."

**Fix:** Run in an external PowerShell window:
```powershell
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'C:\path\to\project'"
```

### "InternalServerError — Failed to provision bot resource"

**Cause:** A conflicting Azure Bot Service resource exists with the same name.

**Fix:**
```bash
az bot delete --name <bot-name> --resource-group <rg>
# Then retry:
a365 setup blueprint --endpoint-only
```

### Agent web app returns 404

- Check Azure logs: `az webapp log tail --name <app> --resource-group <rg>`
- Verify `WEBSITES_PORT=3978` is set
- Verify the startup command runs correctly (check deployment logs)
- Verify `uv` is available — the default startup uses `uv run`

### Agent receives no messages (zero POST requests in logs)

This means the bot endpoint is not registered with A365. Check
`a365.generated.config.json` — if `botId` is null, run:
```bash
a365 setup blueprint --endpoint-only
```

### Server binds to localhost on Azure

**Symptom:** Health probes fail, app keeps restarting.

**Fix:** `host_agent_server.py` must bind to `0.0.0.0` on Azure, not `localhost`.
The code detects Azure via the `WEBSITE_INSTANCE_ID` environment variable.

### OpenTelemetry distro wheel install fails on Azure

**Symptom:** `microsoft-opentelemetry` can't be found during Azure deployment.

**Fix:** The distro source lives in `microsoft/opentelemetry/` within this repo.
Ensure `pyproject.toml` includes it in the wheel packages:
```toml
[tool.hatch.build.targets.wheel]
packages = [".", "microsoft"]
```

### `ChatAgent` import error

**Symptom:** `ImportError: cannot import name 'ChatAgent'`

**Fix:** Pin SDK versions to avoid breaking changes:
```toml
agent-framework-azure-ai==1.0.0b251218
agent-framework-core==1.0.0b251218
```

---

## File Reference

| File | Purpose | Sensitive? |
|------|---------|-----------|
| `.env` | Local secrets — **never commit** | YES |
| `.env.template` | Env var template (empty values) | No |
| `a365.config.json` | CLI config (tenant, resource group, app names) | No (gitignored) |
| `a365.generated.config.json` | CLI state (blueprint IDs, bot registration) | Has secret (gitignored) |
| `manifest/manifest.json` | Teams/M365 app manifest | No (public app IDs only) |
| `host_agent_server.py` | Bot server host with auth & observability | No |
| `agent.py` | Agent logic | No |
| `microsoft/opentelemetry/` | Microsoft OpenTelemetry Distro prototype source | No |
| `microsoft_distro_observability_config.py` | Configures OTel + A365 exporter | No |
| `token_cache.py` | In-memory cache for agentic tokens | No |
