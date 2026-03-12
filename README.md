# Microsoft OpenTelemetry Distro — POC

## Architecture

![Microsoft OTEL Distro Architecture](images/architecture.png)

This project is a **proof of concept** for the [`microsoft-opentelemetry`](https://github.com/hectorhdzg/azure-sdk-for-python/tree/hectorhdzg/microsoftpoc/sdk/monitor/microsoft-opentelemetry) Python package — a unified OpenTelemetry distribution that provides a **single onboarding experience** for observability across **Azure Monitor**, **Microsoft Agent 365 (A365)**, and **OTLP**-compatible backends.

It uses a real Agent Framework agent as the workload to demonstrate the difference between configuring observability manually vs. using the distro.

> For project structure, setup instructions, and environment variables, see [docs/SETUP.md](docs/SETUP.md).
> For design considerations, trade-offs, and multi-language support, see [docs/considerations.md](docs/considerations.md).

## Why This Matters

### 1. Centralized Onboarding — Reducing Customer Confusion

Microsoft customers today face a fragmented observability landscape:

- **Azure Monitor** has its own SDK (`azure-monitor-opentelemetry`), its own setup, and its own documentation
- **Agent 365** has a separate observability SDK (`a365-observability-core`), separate instrumentors, and a completely different configuration model
- **OpenTelemetry OTLP** requires yet another set of exporter packages and manual provider wiring
- **GenAI instrumentations** (OpenAI, LangChain, Semantic Kernel) come from different community packages with different setup patterns

A developer building an AI agent has to discover, learn, and integrate pieces from **multiple product teams** just to get traces flowing. The `microsoft-opentelemetry` distro gives them **one package, one API, one set of docs** — regardless of which backends they target.

### 2. Eliminating Duplication of Effort Across Teams

Without a shared distro, each product team independently solves the same problems:

- Azure Monitor builds its own instrumentation setup logic
- A365 builds its own `TracerProvider` configuration and exporter wiring
- GenAI libraries each ship their own onboarding guides
- Every team writes their own samples, docs, and troubleshooting guides

The distro **converges these efforts into a single codebase** — shared instrumentation setup, shared exporter configuration, shared testing, and a shared surface for customers. Bug fixes and improvements benefit all backends at once.

### 3. Less Boilerplate for Developers

As a direct result of centralization, developers go from **~250 lines of manual setup** (see [`src/observability_config.py`](src/observability_config.py)) — creating tracer providers, initializing 4+ instrumentors individually, managing token caches, handling dependency checks — down to **~60 lines** with a single function call (see [`src/microsoft_distro_observability_config.py`](src/microsoft_distro_observability_config.py)).

## The Solution

The `microsoft-opentelemetry` distro replaces fragmented, product-specific setup with **a single function call**:

```python
from microsoft.opentelemetry import configure_microsoft_opentelemetry

configure_microsoft_opentelemetry(
    enable_a365_agentframework_instrumentation=True,
    enable_a365_openai_instrumentation=True,
    enable_a365_semantickernel_instrumentation=True,
    enable_a365_langchain_instrumentation=True,
)
```

See [`src/microsoft_distro_observability_config.py`](src/microsoft_distro_observability_config.py) for the full implementation.

## What the Distro Handles

- **Exporters**: Azure Monitor, OTLP, and A365 — enabled via parameters or environment variables
- **A365 Instrumentations** (span enrichment & bridging):
  - `AgentFrameworkInstrumentor` — enriches existing AgentFramework spans (normalizes attributes)
  - `OpenAIAgentsTraceInstrumentor` — bridges OpenAI Agents SDK traces → OTel spans
  - `SemanticKernelInstrumentor` — enriches SK spans (normalizes naming)
  - `CustomLangChainInstrumentor` — bridges LangChain callbacks → OTel spans
- **GenAI OTel Instrumentations**: OpenAI, OpenAI Agents, LangChain (community contrib)
- **Standard Instrumentations**: Django, FastAPI, Flask, requests, urllib3, psycopg2

## Configuration Reference

### Quick Start Examples

**Minimal — Azure Monitor only:**

```python
from microsoft.opentelemetry import configure_microsoft_opentelemetry

configure_microsoft_opentelemetry(
    azure_monitor_connection_string="InstrumentationKey=...;IngestionEndpoint=...",
)
```

**OTLP only (no Azure Monitor):**

```python
configure_microsoft_opentelemetry(
    enable_otlp_export=True,
    otlp_endpoint="http://localhost:4318",
)
```

**Azure Monitor + OTLP + A365:**

```python
configure_microsoft_opentelemetry(
    azure_monitor_connection_string="InstrumentationKey=...;IngestionEndpoint=...",
    enable_otlp_export=True,
    enable_a365_export=True,
    a365_token_resolver=lambda agent_id, tenant_id: get_token(agent_id, tenant_id),
)
```

**With GenAI instrumentations (OpenAI + LangChain):**

```python
configure_microsoft_opentelemetry(
    azure_monitor_connection_string="InstrumentationKey=...;IngestionEndpoint=...",
    enable_genai_openai_instrumentation=True,
    enable_genai_openai_agents_instrumentation=True,
    enable_genai_langchain_instrumentation=True,
)
```

**With A365 framework instrumentations:**

```python
configure_microsoft_opentelemetry(
    enable_a365_export=True,
    a365_token_resolver=my_token_resolver,
    enable_a365_openai_instrumentation=True,
    enable_a365_langchain_instrumentation=True,
    enable_a365_semantickernel_instrumentation=True,
    enable_a365_agentframework_instrumentation=True,
)
```

**Environment-variable driven (zero-code config):**

```bash
# Exporters
export APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=..."
export ENABLE_OTLP_EXPORTER=true
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318

# GenAI instrumentations
export ENABLE_GENAI_OPENAI_INSTRUMENTATION=true
export ENABLE_GENAI_OPENAI_AGENTS_INSTRUMENTATION=true
export ENABLE_GENAI_LANGCHAIN_INSTRUMENTATION=true
```

```python
from microsoft.opentelemetry import configure_microsoft_opentelemetry
configure_microsoft_opentelemetry()
```

### Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| **Exporters** | | | |
| `azure_monitor_connection_string` | `str` | Application Insights connection string | `APPLICATIONINSIGHTS_CONNECTION_STRING` env var |
| `enable_azure_monitor_export` | `bool` | Enable Azure Monitor (auto-enabled when connection string is set) | `False` |
| `enable_otlp_export` | `bool` | Enable OTLP exporter | `False` |
| `otlp_endpoint` | `str` | OTLP collector endpoint | `OTEL_EXPORTER_OTLP_ENDPOINT` env var |
| `otlp_protocol` | `str` | `"http/protobuf"` or `"grpc"` | `"http/protobuf"` |
| `otlp_headers` | `str` | OTLP headers (e.g. for authentication) | `OTEL_EXPORTER_OTLP_HEADERS` env var |
| `enable_a365_export` | `bool` | Enable Agent365 exporter | `False` |
| `a365_token_resolver` | `callable` | `(agent_id, tenant_id) -> token` | `None` |
| `a365_cluster_category` | `str` | A365 cluster category | `"prod"` |
| `a365_exporter_options` | `Agent365ExporterOptions` | Advanced A365 exporter config | `None` |
| **GenAI Instrumentations** | | | |
| `enable_genai_openai_instrumentation` | `bool` | Instrument OpenAI SDK (chat, embeddings) | `False` |
| `enable_genai_openai_agents_instrumentation` | `bool` | Instrument OpenAI Agents SDK | `False` |
| `enable_genai_langchain_instrumentation` | `bool` | Instrument LangChain | `False` |
| **A365 Instrumentations** | | | |
| `enable_a365_openai_instrumentation` | `bool` | A365 OpenAI Agents extension | `False` |
| `enable_a365_langchain_instrumentation` | `bool` | A365 LangChain extension | `False` |
| `enable_a365_semantickernel_instrumentation` | `bool` | A365 Semantic Kernel extension | `False` |
| `enable_a365_agentframework_instrumentation` | `bool` | A365 Agent Framework extension | `False` |
| **Pipeline Control** | | | |
| `disable_tracing` | `bool` | Disable trace collection | `False` |
| `disable_logging` | `bool` | Disable log collection | `False` |
| `disable_metrics` | `bool` | Disable metric collection | `False` |
| `resource` | `Resource` | OpenTelemetry Resource | Auto-detected |
| `span_processors` | `list` | Additional `SpanProcessor` instances | `[]` |
| `log_record_processors` | `list` | Additional `LogRecordProcessor` instances | `[]` |
| `metric_readers` | `list` | Additional `MetricReader` instances | `[]` |
| `views` | `list` | Metric `View` instances | `[]` |
| `sampling_ratio` | `float` | Fixed-percentage sampling (0.0–1.0) | not set |
| `traces_per_second` | `float` | Rate-limited sampling TPS | `5.0` |
| `logger_name` | `str` | Python logger name for log capture | `""` (root) |
| `logging_formatter` | `Formatter` | Python `logging.Formatter` for collected logs | `None` |
| `instrumentation_options` | `dict` | Fine-grained instrumentation control (e.g. `{"flask": {"enabled": False}}`) | All supported libs enabled |
| `enable_live_metrics` | `bool` | Azure Monitor live metrics | `True` |
| `enable_performance_counters` | `bool` | Azure Monitor performance counters | `True` |
| `enable_trace_based_sampling_for_logs` | `bool` | Correlate log sampling with trace sampling | `False` |
| `browser_sdk_loader_config` | `dict` | Azure Monitor browser SDK loader configuration | `{}` |

### Environment Variables

| Variable | Maps to | Values |
|----------|---------|--------|
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | `azure_monitor_connection_string` | Connection string |
| `ENABLE_OTLP_EXPORTER` | `enable_otlp_export` | `true` / `false` |
| `ENABLE_A365_EXPORTER` | `enable_a365_export` | `true` / `false` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `otlp_endpoint` | URL |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `otlp_protocol` | `http/protobuf` / `grpc` |
| `OTEL_EXPORTER_OTLP_HEADERS` | `otlp_headers` | key=value pairs |
| `A365_CLUSTER_CATEGORY` | `a365_cluster_category` | string |
| `ENABLE_GENAI_OPENAI_INSTRUMENTATION` | `enable_genai_openai_instrumentation` | `true` / `false` |
| `ENABLE_GENAI_OPENAI_AGENTS_INSTRUMENTATION` | `enable_genai_openai_agents_instrumentation` | `true` / `false` |
| `ENABLE_GENAI_LANGCHAIN_INSTRUMENTATION` | `enable_genai_langchain_instrumentation` | `true` / `false` |
| `ENABLE_A365_OPENAI_INSTRUMENTATION` | `enable_a365_openai_instrumentation` | `true` / `false` |
| `ENABLE_A365_LANGCHAIN_INSTRUMENTATION` | `enable_a365_langchain_instrumentation` | `true` / `false` |
| `ENABLE_A365_SEMANTICKERNEL_INSTRUMENTATION` | `enable_a365_semantickernel_instrumentation` | `true` / `false` |
| `ENABLE_A365_AGENTFRAMEWORK_INSTRUMENTATION` | `enable_a365_agentframework_instrumentation` | `true` / `false` |
| `OTEL_TRACES_EXPORTER` | `disable_tracing` | Set to `none` to disable |
| `OTEL_LOGS_EXPORTER` | `disable_logging` | Set to `none` to disable |
| `OTEL_METRICS_EXPORTER` | `disable_metrics` | Set to `none` to disable |
| `PYTHON_APPLICATIONINSIGHTS_LOGGER_NAME` | `logger_name` | Logger name string |
| `PYTHON_APPLICATIONINSIGHTS_LOGGING_FORMAT` | `logging_formatter` | Logging format string |

### Architecture

```
configure_microsoft_opentelemetry(**kwargs)
│
├─ Step 1: Azure Monitor (if azure_monitor_connection_string provided)
│  └─ Delegates to configure_azure_monitor() from azure-monitor-opentelemetry
│     Sets up TracerProvider, LoggerProvider, MeterProvider, and instrumentations
│
├─ Step 2: Standalone providers (if Azure Monitor disabled)
│  └─ Creates TracerProvider, LoggerProvider, MeterProvider directly
│
├─ Step 3: OTLP exporters (if enable_otlp_export=True)
│  └─ Adds BatchSpanProcessor, BatchLogRecordProcessor, PeriodicExportingMetricReader
│
├─ Step 4: A365 exporter (if enable_a365_export=True)
│  └─ Adds EnrichingBatchSpanProcessor → Agent365Exporter
│
├─ Step 5: Standard instrumentations (only when Azure Monitor is disabled)
│  └─ Django, Flask, FastAPI, Requests, urllib, urllib3, psycopg2, Azure SDK
│
├─ Step 6: A365 observability instrumentations (if any enabled)
│  └─ OpenAI Agents, LangChain, Semantic Kernel, Agent Framework extensions
│
└─ Step 7: GenAI OTel contrib instrumentations (if any enabled)
   └─ OpenAIInstrumentor, OpenAIAgentsInstrumentor, LangchainInstrumentor
```

### Built-in Instrumentations

| Library | Package |
|---------|---------|
| Django | `opentelemetry-instrumentation-django` |
| FastAPI | `opentelemetry-instrumentation-fastapi` |
| Flask | `opentelemetry-instrumentation-flask` |
| Psycopg2 | `opentelemetry-instrumentation-psycopg2` |
| Requests | `opentelemetry-instrumentation-requests` |
| urllib | `opentelemetry-instrumentation-urllib` |
| urllib3 | `opentelemetry-instrumentation-urllib3` |
| Azure SDK | `azure-core` tracing integration |

## License

Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

---

> **Disclaimer:** Parts of this document were generated with the assistance of AI. While efforts have been made to ensure accuracy, there may be inaccuracies. Please verify critical details independently.