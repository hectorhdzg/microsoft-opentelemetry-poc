# Python OpenTelemetry & GenAI Instrumentation — Current State

> **Scope:** Python ecosystem — Azure OpenAI SDK, LangChain, Microsoft Agent Framework, A365 Agent, and how they integrate with OpenTelemetry today. Includes an assessment of where the **Microsoft OpenTelemetry Python Distro** adds value.

---

## 1. Executive Summary

The Python GenAI stack has **fragmented** OpenTelemetry support. Unlike .NET — where first-party SDKs ship native OTel spans — most Python AI libraries require **community instrumentation packages** to produce telemetry. The OpenAI Python SDK needs `opentelemetry-instrumentation-openai-v2`, LangChain needs `opentelemetry-instrumentation-langchain`, and the Agent Framework needs A365-specific bridge instrumentors. There is no unified `IServiceCollection`-style DI pattern — each provider (TracerProvider, MeterProvider, LoggerProvider) must be constructed and wired manually.

The **Microsoft OpenTelemetry Python Distro** (`microsoft.opentelemetry`) solves this directly: a single `configure_microsoft_opentelemetry()` call replaces **~170 lines of manual setup** with **~5-7 lines**, auto-discovers instrumentations, wires up A365 + OTLP + Azure Monitor exporters, and manages sampler configuration. This is where the distro pitch is strongest — Python genuinely needs the consolidation layer that .NET largely doesn't.

---

## 2. SDK OpenTelemetry Compatibility Matrix

| SDK / Library | PyPI Package | OTel-Native? | Instrumentation Required | Telemetry Signals | Semantic Conventions | Notes |
|---|---|---|---|---|---|---|
| **Azure OpenAI SDK** | `openai` | ❌ No | `opentelemetry-instrumentation-openai-v2` 2.3b0 | **Traces** (chat completions, embeddings) | [GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) | Community instrumentation from `opentelemetry-python-contrib`. Monkey-patches the OpenAI client. |
| **LangChain** | `langchain` ≥0.3.0, `langchain-openai` ≥0.3.0 | ❌ No | `opentelemetry-instrumentation-langchain` | **Traces** (chain execution, LLM calls, tool invocations) | GenAI semconv | Community contrib package. Hooks into LangChain callbacks. |
| **OpenAI Agents SDK** | `openai-agents` | ❌ No | `opentelemetry-instrumentation-openai-agents` | **Traces** (agent operations, state transitions) | GenAI semconv | Newer instrumentation for the OpenAI Agents API. |
| **Microsoft Agent Framework** | `agent-framework-azure-ai` 1.0.0rc1 | ❌ No | A365 instrumentor: `microsoft-agents-a365-observability-extensions-agentframework` | **Traces** (agent runs, message processing) | A365-specific attributes | No community OTel instrumentation exists. Must use A365 bridge instrumentor. |
| **A365 Observability SDK** | `microsoft-agents-a365-observability-core` ≥0.2.0.dev0 | ✅ Yes | Built-in | **Traces** (A365-specific spans, span enrichment via `EnrichingBatchSpanProcessor`) | A365-specific attributes | Core SDK: `Agent365Exporter`, token resolvers, cluster categories. Extension packages for OpenAI, LangChain, AgentFramework. |
| **Azure Monitor** | `azure-monitor-opentelemetry` 1.8.6 | ✅ Yes | `configure_azure_monitor()` | **Traces**, **Metrics**, **Logs** | Azure Monitor mapping | Unified package. Bundles auto-instrumentations for `requests`, `flask`, `django`, `psycopg2`, etc. |
| **Django** | `opentelemetry-instrumentation-django` | ✅ (via contrib) | `.instrument()` | **Traces** (HTTP server spans), **Metrics** | HTTP semconv | Separate package per framework — unlike .NET's single `AddAspNetCoreInstrumentation()`. |
| **FastAPI** | `opentelemetry-instrumentation-fastapi` | ✅ (via contrib) | `.instrument()` | **Traces** (HTTP server spans), **Metrics** | HTTP semconv | Same pattern — must install and activate separately. |
| **Flask** | `opentelemetry-instrumentation-flask` | ✅ (via contrib) | `.instrument()` | **Traces**, **Metrics** | HTTP semconv | Same pattern. |
| **Requests** | `opentelemetry-instrumentation-requests` 0.60b0 | ✅ (via contrib) | `.instrument()` | **Traces** (HTTP client spans) | HTTP semconv | Captures outbound HTTP calls. |

### Legend

| Symbol | Meaning |
|---|---|
| ✅ | SDK produces or supports OpenTelemetry-compatible telemetry |
| ❌ | No native OTel telemetry — requires external instrumentation package |

---

## 3. Telemetry Detail by Signal

### 3.1 Traces

| Source | Instrumentor | Span Examples | Key Attributes |
|---|---|---|---|
| OpenAI SDK | `OpenAIInstrumentor` (opentelemetry-instrumentation-openai-v2) | `chat gpt-4o` | `gen_ai.system`, `gen_ai.request.model`, `gen_ai.response.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens` |
| LangChain | `LangchainInstrumentor` | Agent execution, chain steps, tool use | `model`, `tokens`, `tool_name` |
| OpenAI Agents | `OpenAIAgentsInstrumentor` | Agent operations, state transitions | `agent_state`, `action_type` |
| Agent Framework | `AgentFrameworkInstrumentor` (A365 extension) | Agent runs, message processing | `agent_id`, `user_id`, `request_id` |
| A365 OpenAI | `OpenAIAgentsTraceInstrumentor` (A365 extension) | OpenAI calls with A365 enrichment | A365-specific metadata |
| A365 LangChain | `CustomLangChainInstrumentor` (A365 extension) | Chain execution with A365 enrichment | A365-specific metadata |
| Django/FastAPI/Flask | Respective contrib instrumentors | `POST /api/messages`, `GET /health` | `http.method`, `http.route`, `http.status_code` |
| Requests | `RequestsInstrumentor` | `POST https://api.openai.com/...` | `http.method`, `server.address`, `http.response.status_code` |

### 3.2 Metrics

| Source | Meter | Metrics | Description |
|---|---|---|---|
| OpenAI instrumentation | `opentelemetry.instrumentation.openai_v2` | `gen_ai.client.token.usage`, `gen_ai.client.operation.duration` | Token consumption and latency per model call |
| Web framework instrumentors | Per-framework | `http.server.request.duration`, `http.server.active_requests` | Web server throughput and latency |
| Azure Monitor | Azure Monitor SDK | Performance counters, live metrics | Azure-specific operational metrics |

### 3.3 Logs

Python uses standard `logging` module. `LoggerProvider` integration via `opentelemetry-sdk` correlates log records with traces via `TraceId`/`SpanId` context propagation. The distro configures this automatically when Azure Monitor or OTLP logging is enabled.

---

## 4. Typical Python GenAI OTel Architecture

### Without Distro (~170 lines of manual setup)

```python
# 1. Construct TracerProvider manually
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource

resource = Resource.create({"service.name": "my-agent"})
tracer_provider = TracerProvider(resource=resource, sampler=...)

# 2. Add exporters one by one
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=...)))

# 3. Azure Monitor separately
from azure.monitor.opentelemetry import configure_azure_monitor
configure_azure_monitor(connection_string=...)

# 4. A365 exporter separately
from microsoft_agents_a365.observability.core.exporters.agent365_exporter import _Agent365Exporter
from microsoft_agents_a365.observability.core.exporters.enriching_span_processor import _EnrichingBatchSpanProcessor
exporter = _Agent365Exporter(token_resolver=..., cluster_category="prod")
tracer_provider.add_span_processor(_EnrichingBatchSpanProcessor(exporter))

# 5. Initialize A365 core (required before instrumentors)
from microsoft_agents_a365.observability.core import configure
configure()

# 6. Instrument each library manually
from opentelemetry.instrumentation.openai_v2 import OpenAIInstrumentor
OpenAIInstrumentor().instrument()

from microsoft_agents_a365.observability.extensions.langchain import CustomLangChainInstrumentor
CustomLangChainInstrumentor().instrument()

from microsoft_agents_a365.observability.extensions.agentframework import AgentFrameworkInstrumentor
AgentFrameworkInstrumentor().instrument()

# 7. Set global provider
from opentelemetry import trace
trace.set_tracer_provider(tracer_provider)

# ... repeat for MeterProvider, LoggerProvider ...
```

### With Distro (~5 lines)

```python
from microsoft.opentelemetry import configure_microsoft_opentelemetry

configure_microsoft_opentelemetry(
    enable_a365_langchain_instrumentation=True,
    enable_genai_openai_instrumentation=True,
)
```

The distro handles all 7 steps internally: provider construction, exporter wiring, A365 core initialization, instrumentation discovery, sampler configuration, and global provider registration.

---

## 5. Gap Analysis — What the Distro Fills

### 5.1 No Native OTel in AI Libraries

Unlike .NET — where the OpenAI SDK, Agent Framework, and `Microsoft.Extensions.AI` all ship native OTel spans — Python AI libraries produce **zero telemetry** without external instrumentation packages. Every library needs a separate instrumentor:

| Library | Requires |
|---|---|
| OpenAI SDK | `opentelemetry-instrumentation-openai-v2` |
| LangChain | `opentelemetry-instrumentation-langchain` |
| OpenAI Agents | `opentelemetry-instrumentation-openai-agents` |
| Agent Framework | `microsoft-agents-a365-observability-extensions-agentframework` |

The distro auto-discovers and activates these based on configuration flags — developers don't need to know the package names, import paths, or initialization order.

### 5.2 No DI / Builder Pattern

Python has no equivalent to .NET's `IServiceCollection` + `AddOpenTelemetry()`. Each provider must be manually constructed:

```python
tracer_provider = TracerProvider(resource=resource, sampler=sampler)
meter_provider = MeterProvider(resource=resource, metric_readers=[...])
logger_provider = LoggerProvider(resource=resource)
```

The distro provides the "builder pattern" that Python's OTel SDK lacks.

### 5.3 A365 Core Initialization Ordering

A365 instrumentors require `microsoft_agents_a365.observability.core.configure()` to be called **before** any instrumentor is activated. Getting this wrong produces silent failures. The distro handles this ordering automatically.

### 5.4 Multiple Web Frameworks

.NET has one web framework (ASP.NET Core) with one instrumentor. Python has Django, FastAPI, Flask — each needs its own instrumentation package installed and activated. The distro detects which frameworks are present and instruments them automatically.

### 5.5 Sampler Configuration

The distro provides named samplers (`microsoft.rate_limited`, `microsoft.fixed_percentage`) beyond the standard OTel samplers, useful for high-throughput agent scenarios where full trace collection is impractical.

---

## 6. Does Python Need a Microsoft OpenTelemetry Distro?

### 6.1 Yes — Unambiguously

The Python distro is not a "nice-to-have" — it fills **genuine capability gaps** that don't exist in .NET:

| Without distro | With distro |
|---|---|
| ~170 lines of scattered setup across providers, exporters, instrumentors | Single `configure_microsoft_opentelemetry()` call |
| Must know exact import paths for each instrumentor | Auto-discovers and activates instrumentations by flag |
| Must manually initialize A365 core before instrumentors | Handles initialization ordering automatically |
| Manual `TracerProvider` / `MeterProvider` / `LoggerProvider` construction | Providers built and registered internally |
| A365 exporter + OTLP + Azure Monitor wired independently | Unified exporter pipeline from one call |
| Dependency conflicts between instrumentation packages caught at runtime | Pre-validated dependency checking via `get_dist_dependency_conflicts()` |
| Framework detection manual (Django vs FastAPI vs Flask) | Auto-detection of installed frameworks |

### 6.2 The A365 Convergence Story

The distro is the **only way** to get A365 export + GenAI instrumentations + standard OTel export in a single configuration surface. Without it, teams must:

1. Call `microsoft_agents_a365.observability.core.configure()` (A365 init)
2. Construct a `TracerProvider` with correct resource attributes
3. Wire the `Agent365Exporter` with `EnrichingBatchSpanProcessor`
4. Wire OTLP exporter separately
5. Call `configure_azure_monitor()` separately
6. Instrument each library manually in the correct order

The distro collapses all of this into kwargs on a single function.

### 6.3 Current Distro API

```python
from microsoft.opentelemetry import configure_microsoft_opentelemetry

configure_microsoft_opentelemetry(
    # Service identity
    resource=Resource.create({"service.name": "my-agent"}),

    # Exporters
    enable_otlp_export=True,
    otlp_endpoint="http://localhost:4318",
    enable_azure_monitor_export=True,                    # auto-enabled if connection string set
    azure_monitor_connection_string="InstrumentationKey=...",
    enable_a365_export=True,
    a365_token_resolver=my_token_resolver,               # (agent_id, tenant_id) → token
    a365_cluster_category="prod",

    # GenAI instrumentations (community OTel contrib)
    enable_genai_openai_instrumentation=True,
    enable_genai_openai_agents_instrumentation=True,
    enable_genai_langchain_instrumentation=True,

    # A365 instrumentations (bridge instrumentors)
    enable_a365_openai_instrumentation=True,
    enable_a365_langchain_instrumentation=True,
    enable_a365_agentframework_instrumentation=True,

    # Sampling
    sampling_ratio=0.5,                                  # or traces_per_second=100
)
```

### 6.4 Value by Scenario

| Scenario | Value | Why |
|---|---|---|
| **A365-deployed Python agents** | **High** | A365 exporter + instrumentors + OTLP + Azure Monitor unified. Only viable path without manual plumbing. |
| **LangChain app needing observability** | **High** | Collapses instrumentation discovery + provider setup + exporter wiring into one call. |
| **Team running Python + .NET agents** | **High** | Cross-language consistency — same env vars, same parameter names, same behavior as .NET distro. |
| **Enterprise with many Python services** | **High** | Standardized config prevents each team from reinventing OTel setup. |
| **Simple Python app, Azure Monitor only** | Moderate | `azure-monitor-opentelemetry` already works, but distro adds GenAI instrumentation + A365 export path. |
| **Simple Python app, OTLP only** | Moderate | Still saves significant boilerplate vs manual provider construction. |

---

## 7. Exporter & Backend Topology

### Local Development

```
Python Agent (localhost:8080)
  │
  ├── OTLP HTTP (:4318) ──→ OTel Collector
  │                            ├──→ Jaeger (:16686) — trace visualization
  │                            └──→ Prometheus (:9090) — metrics dashboard
  │
  ├── Console ──→ stdout (SimpleSpanProcessor + ConsoleSpanExporter)
  │
  └── A365 Exporter ──→ Agent365 cloud backend (via token auth)
```

### Production (Azure)

```
Python Agent (App Service / AKS / A365)
  │
  ├── Azure Monitor Exporter ──→ Application Insights
  │                                ├── Transaction Search (traces)
  │                                ├── Metrics Explorer
  │                                ├── Log Analytics (KQL)
  │                                └── Live Metrics Stream
  │
  ├── A365 Exporter ──→ Agent365 cloud backend
  │                      └── EnrichingBatchSpanProcessor (span enrichment)
  │
  └── OTLP (optional) ──→ Any OTel-compatible backend
```

---

## 8. OpenAI Instrumentation Deep Dive

The `opentelemetry-instrumentation-openai-v2` package is the primary GenAI instrumentation for Python. Unlike .NET (where the SDK emits spans natively), this is a **monkey-patching** instrumentor.

### Activation

```python
# Via distro
configure_microsoft_opentelemetry(enable_genai_openai_instrumentation=True)

# Manual
from opentelemetry.instrumentation.openai_v2 import OpenAIInstrumentor
OpenAIInstrumentor().instrument()
```

### Trace Attributes (GenAI Semantic Conventions)

| Attribute | Example Value | Description |
|---|---|---|
| `gen_ai.system` | `openai` | AI system identifier |
| `gen_ai.operation.name` | `chat` | Operation type |
| `gen_ai.request.model` | `gpt-4o` | Requested model |
| `gen_ai.response.model` | `gpt-4o-2024-08-06` | Actual model used |
| `gen_ai.usage.input_tokens` | `125` | Prompt token count |
| `gen_ai.usage.output_tokens` | `84` | Completion token count |
| `server.address` | `myresource.openai.azure.com` | Endpoint host |

### Metrics

| Metric | Type | Unit | Description |
|---|---|---|---|
| `gen_ai.client.token.usage` | Histogram | `token` | Token count per request |
| `gen_ai.client.operation.duration` | Histogram | `s` | End-to-end call duration |

### Key Difference from .NET

In .NET, the OpenAI SDK emits OTel spans natively via `AppContext.SetSwitch`. In Python, the spans come from the external instrumentor monkey-patching `openai.ChatCompletion.create()` and related methods. Same semantic conventions, different mechanism — the distro abstracts this difference.

---

## 9. A365 Observability SDK (Python)

The A365 Python Observability SDK mirrors the .NET one (see DOTNET-OTEL-STATE.md, section 2) but with Python-specific packaging:

| Package | Purpose |
|---|---|
| `microsoft-agents-a365-observability-core` | Core — `Agent365Exporter`, `EnrichingBatchSpanProcessor`, token resolvers, cluster categories |
| `microsoft-agents-a365-observability-extensions-openai` | `OpenAIAgentsTraceInstrumentor` — OpenAI calls with A365 span enrichment |
| `microsoft-agents-a365-observability-extensions-langchain` | `CustomLangChainInstrumentor` — LangChain execution with A365 enrichment |
| `microsoft-agents-a365-observability-extensions-agentframework` | `AgentFrameworkInstrumentor` — Agent Framework runs with A365 metadata |

**Key difference from .NET:** The Python A365 SDK requires the distro (or manual plumbing) to set up the OTel pipeline. The .NET A365 SDK (`AddA365Tracing()`) handles its own OTel pipeline internally. In Python, `microsoft_agents_a365.observability.core.configure()` only initializes A365 internals — it does **not** create a `TracerProvider` or wire exporters. That's the distro's job.

---

## 10. Recommendations

### Short-term

1. **Use the distro for all Python GenAI projects** — The manual setup is error-prone, verbose, and hard to maintain. The distro is the correct default.
2. **Standardize on env vars** — Use `ENABLE_OTLP_EXPORTER`, `APPLICATIONINSIGHTS_CONNECTION_STRING`, `ENABLE_A365_EXPORTER` consistently across all deployments.
3. **Enable both GenAI and A365 instrumentations** — They serve different purposes (GenAI = OTel semconv compliance, A365 = A365-specific enrichment). Both can coexist.

### Medium-term

4. **Parity with .NET distro** — Ensure the Python and .NET distros expose matching configuration surfaces for cross-language teams.
5. **Dependency conflict resolution** — The distro's `get_dist_dependency_conflicts()` should surface clear error messages when instrumentation packages conflict.

### Long-term

6. **Push for native OTel in Python AI SDKs** — Advocate for `openai`, `langchain`, and `agent-framework` to emit OTel spans natively (like their .NET counterparts), reducing the need for monkey-patching instrumentors.

---

## 11. Package Reference Summary

### Core OTel

| Package | Version | Role |
|---|---|---|
| `opentelemetry-sdk` | 1.39.0 | Core OTel SDK (TracerProvider, MeterProvider, LoggerProvider) |
| `opentelemetry-api` | 1.39.0 | Core OTel API (tracer, meter, context propagation) |
| `opentelemetry-exporter-otlp-proto-http` | 1.39.0 | OTLP HTTP exporter |

### Azure

| Package | Version | Role |
|---|---|---|
| `azure-monitor-opentelemetry` | 1.8.6 | Unified Azure Monitor exporter + auto-instrumentations |
| `azure-identity` | ≥1.16.0 | Managed identity / credential auth |

### GenAI Instrumentations

| Package | Version | Role |
|---|---|---|
| `opentelemetry-instrumentation-openai-v2` | 2.3b0 | OpenAI SDK instrumentation (monkey-patch) |
| `opentelemetry-instrumentation-openai-agents` | (beta) | OpenAI Agents SDK instrumentation |
| `opentelemetry-instrumentation-langchain` | (contrib) | LangChain instrumentation |
| `opentelemetry-instrumentation-requests` | 0.60b0 | Requests HTTP client instrumentation |

### A365 Observability

| Package | Version | Role |
|---|---|---|
| `microsoft-agents-a365-observability-core` | ≥0.2.0.dev0 | A365 exporter, span processor, core init |
| `microsoft-agents-a365-observability-extensions-openai` | ≥0.1.0.dev0 | A365 OpenAI bridge instrumentor |
| `microsoft-agents-a365-observability-extensions-langchain` | ≥0.1.0.dev0 | A365 LangChain bridge instrumentor |
| `microsoft-agents-a365-observability-extensions-agentframework` | ≥0.1.0.dev0 | A365 Agent Framework bridge instrumentor |

### Agent Framework

| Package | Version | Role |
|---|---|---|
| `agent-framework-azure-ai` | 1.0.0rc1 | Agent Framework with Azure AI integration |
| `agent-framework-core` | 1.0.0rc1 | Agent Framework core |
| `microsoft-agents-hosting-aiohttp` | (latest) | aiohttp-based agent hosting |
| `microsoft-agents-activity` | (latest) | Agent activity model |

### AI SDKs

| Package | Version | Role |
|---|---|---|
| `langchain` | ≥0.3.0 | LangChain orchestration framework |
| `langchain-openai` | ≥0.3.0 | LangChain OpenAI integration |
| `azure-ai-agents` | 1.2.0b5 | Azure AI Agents SDK |
| `azure-ai-projects` | 2.0.0b3 | Azure AI Projects SDK |
