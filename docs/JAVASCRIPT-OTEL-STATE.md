# JavaScript / Node.js OpenTelemetry & GenAI Instrumentation — Current State

> **Scope:** JavaScript/Node.js ecosystem — Azure OpenAI SDK, LangChain.js, A365 Agent, and how they integrate with OpenTelemetry today. Includes an assessment of where a **Microsoft OpenTelemetry JS Distro** would add value.

---

## 1. Executive Summary

The JavaScript/Node.js GenAI stack has **mixed** OpenTelemetry support. The **Azure OpenAI SDK** (`@azure/openai`) does not emit native OTel spans — it requires the community `@opentelemetry/instrumentation-openai` package. **LangChain.js** has emerging OTel support via callbacks. The **A365 Observability SDK exists in Node.js** with its own exporter and instrumentations. **Microsoft Agent Framework does not have a JS/Node.js SDK** — though Azure and LangChain are planning support for it.

The Node.js OTel ecosystem sits between .NET and Python: it has a decent auto-instrumentation story (`@opentelemetry/auto-instrumentations-node`) for HTTP/Express/etc., but GenAI-specific instrumentation is fragmented and immature. A **Microsoft OpenTelemetry JS Distro** would add the most value by unifying A365 export with standard OTel exporters and auto-registering GenAI instrumentations — mirroring what the Python distro already does.

---

## 2. SDK OpenTelemetry Compatibility Matrix

| SDK / Library | npm Package | OTel-Native? | Instrumentation Required | Telemetry Signals | Semantic Conventions | Notes |
|---|---|---|---|---|---|---|
| **Azure OpenAI SDK** | `@azure/openai` | ❌ No | `@opentelemetry/instrumentation-openai` (community) | **Traces** (chat completions, embeddings) | [GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) | Community instrumentation. Not yet stable. |
| **OpenAI Node.js SDK** | `openai` | ❌ No | Same as above | Same as above | GenAI semconv | `@azure/openai` wraps this; share the same instrumentation. |
| **LangChain.js** | `langchain`, `@langchain/openai` | ⚠️ Partial | Built-in callback-based tracing + community OTel bridge | **Traces** (chain execution, LLM calls, tool invocations) | Partial GenAI semconv | LangChain.js has its own tracing system (LangSmith callbacks). OTel integration is via bridge adapters — not as mature as Python's `opentelemetry-instrumentation-langchain`. |
| **A365 Observability SDK** | A365 Node.js observability packages | ✅ Yes | Built-in | **Traces** (A365-specific spans, span enrichment) | A365-specific attributes | Mirrors the Python/`.NET A365 observability SDK. Provides A365 exporter, span processors, and framework extensions for Node.js. |
| **Microsoft Agent Framework** | N/A | N/A | N/A | N/A | N/A | **No Node.js SDK exists.** Azure and LangChain teams are planning future support. |
| **Express** | `@opentelemetry/instrumentation-express` | ✅ (via contrib) | Auto-instrumented via `@opentelemetry/auto-instrumentations-node` | **Traces** (HTTP server spans), **Metrics** | HTTP semconv | Mature, stable. Part of auto-instrumentations meta-package. |
| **Fastify** | `@opentelemetry/instrumentation-fastify` | ✅ (via contrib) | Same — auto-instrumented | **Traces**, **Metrics** | HTTP semconv | Same pattern. |
| **HTTP (node:http)** | `@opentelemetry/instrumentation-http` | ✅ (via contrib) | Auto-instrumented | **Traces** (HTTP client + server spans) | HTTP semconv | Foundation for all HTTP-based instrumentations. |
| **Azure SDK (core)** | `@azure/core-tracing` | ✅ Yes | Automatic (when OTel is configured) | **Traces** (HTTP pipeline spans) | Azure SDK conventions | Every `@azure/*` client emits spans via `@azure/core-tracing`. |
| **Azure Monitor** | `@azure/monitor-opentelemetry` | ✅ Yes | `useAzureMonitor()` | **Traces**, **Metrics**, **Logs** | Azure Monitor mapping | Unified package. Auto-instruments common Node.js libraries. |

### Legend

| Symbol | Meaning |
|---|---|
| ✅ | SDK produces or supports OpenTelemetry-compatible telemetry |
| ⚠️ | Partial or emerging support; requires bridge adapter |
| ❌ | No native OTel telemetry — requires external instrumentation package |

---

## 3. Telemetry Detail by Signal

### 3.1 Traces

| Source | Instrumentor | Span Examples | Key Attributes |
|---|---|---|---|
| OpenAI SDK | `@opentelemetry/instrumentation-openai` | `chat gpt-4o` | `gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens` |
| LangChain.js | LangSmith callback → OTel bridge | Chain execution, LLM calls, tool invocations | `model`, `tokens`, `tool_name` |
| A365 SDK | A365 Node.js instrumentors | A365-specific agent spans, enriched spans | A365-specific metadata, token/session data |
| Express/Fastify | `@opentelemetry/instrumentation-express` / `-fastify` | `POST /api/messages`, `GET /health` | `http.method`, `http.route`, `http.status_code` |
| HTTP client | `@opentelemetry/instrumentation-http` | `POST https://api.openai.com/...` | `http.method`, `server.address` |
| Azure SDK | `@azure/core-tracing` | Azure service calls | `az.namespace`, `az.schema_url` |

### 3.2 Metrics

| Source | Metrics | Description |
|---|---|---|
| HTTP instrumentation | `http.server.request.duration`, `http.server.active_requests` | Web server throughput and latency |
| OpenAI instrumentation | `gen_ai.client.token.usage`, `gen_ai.client.operation.duration` | Token consumption and call latency (when instrumentation supports it) |
| Azure Monitor | Performance counters, live metrics | Azure-specific operational metrics |

### 3.3 Logs

Node.js logging integration via `@opentelemetry/instrumentation-winston` or `@opentelemetry/instrumentation-pino`. Log records are correlated with traces via `TraceId`/`SpanId` context propagation.

---

## 4. Typical Node.js GenAI OTel Architecture

### Current State (manual setup)

```javascript
const { NodeTracerProvider } = require('@opentelemetry/sdk-trace-node');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-http');
const { BatchSpanProcessor } = require('@opentelemetry/sdk-trace-base');
const { Resource } = require('@opentelemetry/resources');
const { registerInstrumentations } = require('@opentelemetry/instrumentation');

// 1. Create provider
const provider = new NodeTracerProvider({
  resource: new Resource({ 'service.name': 'my-agent' }),
});

// 2. Add exporters
provider.addSpanProcessor(new BatchSpanProcessor(new OTLPTraceExporter({
  url: 'http://localhost:4318/v1/traces',
})));

// 3. Register provider
provider.register();

// 4. Register instrumentations manually
const { HttpInstrumentation } = require('@opentelemetry/instrumentation-http');
const { ExpressInstrumentation } = require('@opentelemetry/instrumentation-express');
// GenAI instrumentation — if available
registerInstrumentations({
  instrumentations: [
    new HttpInstrumentation(),
    new ExpressInstrumentation(),
    // ... GenAI instrumentors ...
  ],
});

// 5. Azure Monitor — separate path
const { useAzureMonitor } = require('@azure/monitor-opentelemetry');
useAzureMonitor({ connectionString: '...' });

// 6. A365 exporter — separate SDK, separate setup
// ... A365 Node.js observability SDK wiring ...
```

### With Distro (proposed)

```javascript
const { configureMicrosoftOpenTelemetry } = require('microsoft-opentelemetry');

configureMicrosoftOpenTelemetry({
  serviceName: 'my-agent',
  enableGenAI: true,
  enableOtlpExport: true,
  azureMonitorConnectionString: process.env.APPLICATIONINSIGHTS_CONNECTION_STRING,
  enableA365Export: true,
  a365TokenResolver: myTokenResolver,
});
```

---

## 5. Gap Analysis — What's Missing

### 5.1 GenAI Instrumentation Immaturity

The Node.js GenAI instrumentation ecosystem is less mature than Python's:

| Library | Python Instrumentation | Node.js Instrumentation |
|---|---|---|
| OpenAI SDK | `opentelemetry-instrumentation-openai-v2` (beta, works) | `@opentelemetry/instrumentation-openai` (early, less tested) |
| LangChain | `opentelemetry-instrumentation-langchain` (contrib) | No direct OTel instrumentor — relies on LangSmith callback bridge |
| Agent Framework | A365 `AgentFrameworkInstrumentor` | N/A — no Agent Framework in Node.js |
| OpenAI Agents | `opentelemetry-instrumentation-openai-agents` (beta) | Not yet available for Node.js |

### 5.2 No Agent Framework

Microsoft Agent Framework has no Node.js SDK. This means the Agent Framework OTel story is irrelevant for JS today. If Azure and LangChain deliver planned support, this gap closes.

### 5.3 LangChain.js OTel Bridge

LangChain.js uses its own tracing system (LangSmith callbacks). OTel integration requires a bridge adapter that converts LangSmith spans to OTel spans. This is less clean than Python's direct `LangchainInstrumentor` and may lose attributes in translation.

### 5.4 Auto-Instrumentation vs GenAI

Node.js has a strong auto-instrumentation story for HTTP/Express/database via `@opentelemetry/auto-instrumentations-node`. But this meta-package does **not** include GenAI instrumentations. There's a gap between "auto-instrument everything HTTP" and "also instrument my AI calls."

---

## 6. Does Node.js Need a Microsoft OpenTelemetry Distro?

### 6.1 The Primary Value: A365 Convergence (Same as .NET and Python)

The A365 Node.js Observability SDK already exists with its own exporter and instrumentations. Developers building Node.js GenAI apps use standard `@opentelemetry/sdk-trace-node` with OTLP / Azure Monitor exporters separately. Same problem as .NET and Python — **two separate OTel pipelines**.

| Without distro | With distro |
|---|---|
| A365 Node.js SDK sets up its own OTel pipeline with A365 exporter | Single `configureMicrosoftOpenTelemetry()` unifies A365 + OTLP + Azure Monitor |
| Manual `NodeTracerProvider` construction + exporter wiring | Providers built and registered internally |
| Must discover and install GenAI instrumentation packages | Auto-discovers available instrumentations |
| A365 pipeline and OTLP pipeline configured independently | Single pipeline, consistent resource attributes, sampling |
| `useAzureMonitor()` called separately from everything else | Unified exporter configuration |

### 6.2 Secondary Benefits

- **Cross-language consistency** — Teams running Python + .NET + Node.js agents get the same env vars (`ENABLE_OTLP_EXPORTER`, `APPLICATIONINSIGHTS_CONNECTION_STRING`), same parameter names, same behavior
- **GenAI instrumentation gap** — Node.js GenAI instrumentations are immature. A distro that bundles and validates them provides more value than in .NET (where SDKs emit natively) 
- **Enterprise standardization** — "Golden path" config for Node.js services alongside Python and .NET

### 6.3 What the Distro is NOT

Same principle as .NET and Python: **pipeline configurator, not a capability enabler**. The distro:

- Depends only on OTel SDK + exporter packages
- Registers instrumentations that are installed — does not bundle AI SDKs
- Configures the collection pipeline (providers, exporters, resource attributes, sampling)

### 6.4 Proposed API

```javascript
const { configureMicrosoftOpenTelemetry } = require('microsoft-opentelemetry');

configureMicrosoftOpenTelemetry({
  serviceName: 'my-agent',
  enableGenAI: true,                          // auto-registers GenAI instrumentations if installed
  enableOtlpExport: true,
  otlpEndpoint: 'http://localhost:4318',
  azureMonitorConnectionString: connectionString,
  enableA365Export: true,
  a365TokenResolver: tokenResolver,
  a365ClusterCategory: 'prod',
});
```

### 6.5 Value by Scenario

| Scenario | Value | Why |
|---|---|---|
| **A365-deployed Node.js agents** | **High** | Unifies A365 exporter with OTLP + Azure Monitor — same convergence story as .NET and Python |
| **Team running Python + .NET + Node.js agents** | **High** | Cross-language consistency — same env vars, same config surface |
| **LangChain.js app needing observability** | **High** | Distro can bundle/validate the LangSmith→OTel bridge, handle provider setup |
| **Enterprise with many JS services** | **High** | Standardized "golden path" prevents each team from reinventing OTel setup |
| **Simple Express app, Azure Monitor only** | Moderate | `@azure/monitor-opentelemetry` already covers it, but distro adds GenAI + A365 |
| **Simple Node.js app, OTLP only** | Low | `@opentelemetry/auto-instrumentations-node` already handles HTTP/Express well |

---

## 7. Exporter & Backend Topology

### Local Development

```
Node.js Agent (localhost:3000)
  │
  ├── OTLP HTTP (:4318) ──→ OTel Collector
  │                            ├──→ Jaeger (:16686) — trace visualization
  │                            └──→ Prometheus (:9090) — metrics dashboard
  │
  ├── Console ──→ stdout (ConsoleSpanExporter)
  │
  └── A365 Exporter ──→ Agent365 cloud backend (via token auth)
```

### Production (Azure)

```
Node.js Agent (App Service / AKS / A365)
  │
  ├── Azure Monitor Exporter ──→ Application Insights
  │                                ├── Transaction Search (traces)
  │                                ├── Metrics Explorer
  │                                ├── Log Analytics (KQL)
  │                                └── Live Metrics Stream
  │
  ├── A365 Exporter ──→ Agent365 cloud backend
  │
  └── OTLP (optional) ──→ Any OTel-compatible backend
```

---

## 8. OpenAI Instrumentation Deep Dive

### Activation

```javascript
// Via auto-instrumentations (if included)
const { OpenAIInstrumentation } = require('@opentelemetry/instrumentation-openai');
registerInstrumentations({
  instrumentations: [new OpenAIInstrumentation()],
});

// Via distro (proposed)
configureMicrosoftOpenTelemetry({ enableGenAI: true });
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

### Key Difference from .NET and Python

- **.NET**: OpenAI SDK emits OTel spans natively via `AppContext.SetSwitch`
- **Python**: External instrumentor monkey-patches `openai.ChatCompletion.create()`
- **Node.js**: External instrumentor wraps `openai` SDK methods — similar to Python's approach but less mature

---

## 9. Comparison with .NET and Python

| Aspect | .NET | Python | Node.js |
|---|---|---|---|
| **OpenAI SDK OTel** | ✅ Native (feature flag) | ❌ Needs instrumentor | ❌ Needs instrumentor |
| **Agent Framework** | ✅ `ChatClientAgent` + `.UseOpenTelemetry()` | ❌ Needs A365 instrumentor | N/A — no SDK |
| **LangChain OTel** | N/A — no .NET LangChain | ❌ Needs instrumentor | ⚠️ LangSmith callback bridge |
| **A365 Observability SDK** | ✅ `AddA365Tracing()` | ✅ A365 core + extensions | ✅ A365 Node.js SDK |
| **DI / Builder pattern** | ✅ `IServiceCollection` | ❌ Manual providers | ❌ Manual providers |
| **Auto-instrumentation** | Per-package (AspNetCore, Http) | Per-package + auto-detect | `@opentelemetry/auto-instrumentations-node` meta-package |
| **GenAI instrumentation maturity** | ✅ High (native in SDKs) | 🟡 Moderate (community contrib) | 🔴 Low (early stage) |
| **Distro value** | Moderate (convergence + config) | **High** (fills genuine gaps) | **High** (immature ecosystem + convergence) |

---

## 10. Recommendations

### Short-term

1. **Validate A365 Node.js Observability SDK** — Confirm the exact npm packages, API surface, and maturity level. Mirror the Python/`.NET analysis with actual package contents.
2. **Assess LangChain.js OTel bridge** — Determine if the LangSmith→OTel bridge produces GenAI semconv-compliant spans or lossy translations.
3. **Track Agent Framework Node.js timeline** — Monitor Azure and LangChain plans for Agent Framework JS support.

### Medium-term

4. **Build JS distro** — `microsoft-opentelemetry` npm package with `configureMicrosoftOpenTelemetry()`. Prioritize A365 convergence + GenAI instrumentation bundling.
5. **Parity with Python distro** — Same configuration surface, same env vars, same behavior.

### Long-term

6. **Push for native OTel in Node.js AI SDKs** — Same advocacy as Python: `openai` and `@langchain/*` should emit OTel spans natively.
7. **Agent Framework Node.js OTel** — When Agent Framework ships for Node.js, ensure OTel integration is included from day one.

---

## 11. Package Reference Summary

### Core OTel

| Package | Role |
|---|---|
| `@opentelemetry/sdk-trace-node` | Core trace SDK for Node.js |
| `@opentelemetry/sdk-metrics` | Metrics SDK |
| `@opentelemetry/api` | OTel API (tracer, meter, context) |
| `@opentelemetry/resources` | Resource detection and configuration |
| `@opentelemetry/exporter-trace-otlp-http` | OTLP HTTP trace exporter |
| `@opentelemetry/exporter-metrics-otlp-http` | OTLP HTTP metrics exporter |
| `@opentelemetry/auto-instrumentations-node` | Meta-package: auto-instruments HTTP, Express, Fastify, etc. |

### Azure

| Package | Role |
|---|---|
| `@azure/monitor-opentelemetry` | Unified Azure Monitor exporter + auto-instrumentations |
| `@azure/openai` | Azure OpenAI client |
| `@azure/identity` | Managed identity / credential auth |
| `@azure/core-tracing` | Azure SDK built-in OTel span emission |

### GenAI Instrumentations

| Package | Role |
|---|---|
| `@opentelemetry/instrumentation-openai` | OpenAI SDK instrumentation (community, early stage) |

### A365 Observability

| Package | Role |
|---|---|
| A365 Node.js observability core | A365 exporter, span processors, token resolvers |
| A365 Node.js observability extensions | Framework-specific instrumentors |

### Web Frameworks

| Package | Role |
|---|---|
| `@opentelemetry/instrumentation-http` | Node.js HTTP client + server instrumentation |
| `@opentelemetry/instrumentation-express` | Express.js instrumentation |
| `@opentelemetry/instrumentation-fastify` | Fastify instrumentation |
| `@opentelemetry/instrumentation-winston` | Winston logger → OTel log correlation |
| `@opentelemetry/instrumentation-pino` | Pino logger → OTel log correlation |
