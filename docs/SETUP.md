# Project Setup & Structure

## Project Structure

```
├── README.md                                # POC specification
├── pyproject.toml                           # Python project config & dependencies
├── .env.template                            # Environment variable template
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
├── vendor/                                  # Vendored microsoft-opentelemetry wheel
├── docs/                                    # Design docs and demo scripts
└── images/                                  # Architecture diagrams
```

## Prerequisites

- Python 3.11+
- Azure OpenAI API credentials (API key or Azure Identity)

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

2. **Configure environment** — copy `.env.template` to `.env` and fill in your Azure OpenAI credentials:
   ```bash
   cp .env.template .env
   # Edit .env with your AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT
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

| Variable | Purpose |
|---|---|
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name (e.g., `gpt-4.1`) |
| `AZURE_OPENAI_API_VERSION` | Azure OpenAI API version |
| `ENABLE_INSTRUMENTATION=true` | Turns on span creation in AgentFramework SDK |
| `ENABLE_SENSITIVE_DATA=true` | Include message content in spans |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Azure Monitor (optional) |
| `ENABLE_A365_EXPORTER=true` | Send spans to A365 cloud backend (optional) |

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
