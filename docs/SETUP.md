# Project Setup & Structure

## Project Structure

```
├── README.md                                # POC specification
├── pyproject.toml                           # Python project config & dependencies
├── .env.template                            # Env template — standard (console, OTLP, Azure Monitor)
├── .env.a365                                # Env template — A365 + Azure Monitor + OTLP
├── src/
│   ├── start_with_generic_host.py           # Entry point
│   ├── agent.py                             # Agent Framework agent (Azure OpenAI)
│   ├── agent_interface.py                   # Abstract base class for agents
│   ├── host_agent_server.py                 # aiohttp server on port 3978
│   ├── local_authentication_options.py      # Auth options from environment
│   ├── observability_config.py              # A365 manual approach (~250 lines)
│   ├── microsoft_distro_observability_config.py  # Microsoft Distro approach (~60 lines)
│   ├── instrumentation_span_processor.py    # Shared SpanProcessor for metadata
│   ├── token_cache.py                       # Token cache for A365 exporter auth
│   └── ToolingManifest.json                 # MCP tool manifest
├── microsoft/opentelemetry/                 # Microsoft OpenTelemetry Distro prototype source
├── docker/                                  # Local OTLP stack (OTel Collector + Jaeger)
│   ├── docker-compose.yml                   # Starts collector and Jaeger
│   └── otel-collector-config.yml            # Collector pipeline config
├── docs/                                    # Design docs and demo scripts
└── images/                                  # Architecture diagrams
```

## Prerequisites

- Python 3.11+
- Azure OpenAI API credentials (API key or Azure Identity)
- Docker (optional — only needed for OTLP/Jaeger setup)

## Quick Start

1. **Clone and install**:
   ```bash
   git clone https://github.com/hectorhdzg/microsoft-opentelemetry-poc.git
   cd microsoft-opentelemetry-poc
   python -m venv .venv
   .venv/Scripts/activate   # Windows
   # source .venv/bin/activate  # Linux/macOS
   pip install -e .
   ```

2. **Configure environment** — pick the template that matches your setup:

   **Option A: Standard (no A365 auth)**
   Use this for local development. Telemetry prints to console by default. Uncomment OTLP and/or Azure Monitor lines to enable those exporters.
   ```bash
   cp .env.template .env
   # Edit .env — fill in AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_API_VERSION
   # Optionally uncomment APPLICATIONINSIGHTS_CONNECTION_STRING for Azure Monitor
   # Optionally uncomment ENABLE_OTLP_EXPORTER + OTEL_EXPORTER_OTLP_ENDPOINT for OTLP
   ```
   For OTLP, start the Docker stack first:
   ```bash
   docker compose -f docker/docker-compose.yml up -d
   ```
   Then browse traces in **Jaeger UI** at [http://localhost:16686](http://localhost:16686).

   **Option B: A365 + Azure Monitor (full cloud)**
   Use this when you have A365 agentic auth credentials. Includes Azure Monitor and optional OTLP.
   ```bash
   cp .env.a365 .env
   # Edit .env — fill in Azure OpenAI credentials, APPLICATIONINSIGHTS_CONNECTION_STRING,
   # and the A365 auth block (CLIENTID, CLIENTSECRET, TENANTID, SCOPES)
   ```

3. **Run the agent**:
   ```bash
   python src/start_with_generic_host.py
   ```

4. **Test with Agents Playground**:
   ```bash
   winget install Microsoft.M365AgentsPlayground
   ```
   Connect the Playground to `http://localhost:3978/api/messages`.

## Switching Between Approaches

In `src/host_agent_server.py`, change the import:

```python
# A365 manual approach (~250 lines of setup)
from observability_config import setup_observability

# Microsoft Distro approach (~60 lines of setup)
from microsoft_distro_observability_config import setup_observability
```

Both expose the same `setup_observability()` API — it's a drop-in swap.

## Environment Variables

### Required (both templates)

| Variable | Purpose |
|---|---|
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name (e.g., `gpt-4.1`) |
| `AZURE_OPENAI_API_VERSION` | Azure OpenAI API version |
| `ENABLE_OTEL=true` | Enable OTel spans in AgentFramework SDK |
| `ENABLE_SENSITIVE_DATA=true` | Include message content in spans |

### Cloud exporters (`.env.a365` only)

| Variable | Purpose |
|---|---|
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Azure Monitor / Application Insights |
| `ENABLE_A365_EXPORTER=true` | Send spans to A365 cloud backend |
| `ENABLE_OTLP_EXPORTER=true` | Send spans via OTLP (e.g. Jaeger, Aspire) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP collector endpoint |

### A365 agentic auth (`.env.a365` only)

| Variable | Purpose |
|---|---|
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID` | App registration client ID |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET` | App registration client secret |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID` | Azure AD tenant ID |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__SCOPES` | Auth scopes |

## Key Files

| File | Description |
|---|---|
| `src/observability_config.py` | **A365 manual approach** — ~250 lines. Manual TracerProvider setup, 4 separate instrumentor initializations, token cache management, logger configuration. |
| `src/microsoft_distro_observability_config.py` | **Microsoft Distro approach** — ~60 lines. Single `configure_microsoft_opentelemetry()` call replaces all of the above. |
| `src/instrumentation_span_processor.py` | Shared `SpanProcessor` that stamps every span with metadata about which setup approach and instrumentors are active. Useful for comparing output between the two approaches. |
| `src/token_cache.py` | Token cache for A365 exporter authentication. Used by both approaches. |
| `src/agent.py` | The actual agent workload — Agent Framework agent using Azure OpenAI with MCP tool integration. |
| `src/host_agent_server.py` | aiohttp server that hosts the agent on port 3978. This is where the observability import switch happens. |
| `src/start_with_generic_host.py` | Entry point. Creates an `AgentFrameworkAgent` and starts the host server. |
