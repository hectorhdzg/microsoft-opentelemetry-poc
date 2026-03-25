# .NET OpenTelemetry & GenAI Instrumentation — Current State

> **Scope:** .NET ecosystem — Azure OpenAI SDK, Microsoft Agent Framework, A365 Agent, and how they integrate with OpenTelemetry today. Includes an assessment of where a **Microsoft OpenTelemetry SDK (distro)** adds value.

---

## 1. Executive Summary

The .NET GenAI stack has strong—but fragmented—OpenTelemetry support. The **Azure OpenAI SDK** ships native OTel spans behind an experimental feature flag, **Microsoft Agent Framework** supports OTel via `Microsoft.Extensions.AI` integration and its own `Microsoft.Agents.AI` activity sources, ASP.NET Core and HttpClient have mature community instrumentations, and Azure Monitor provides a unified exporter. However, each project must still wire up **30-70 lines of boilerplate** to configure providers, exporters, sources, and feature flags, and the level of OTel support varies significantly by which API surface is used.

A **Microsoft OpenTelemetry .NET Distro** would collapse this setup into a single `.AddMicrosoftOpenTelemetry()` call, auto-register known GenAI activity source patterns as strings (e.g. `"OpenAI.*"`, `"Microsoft.Agents.*"`, `"Microsoft.Extensions.AI"`) with **zero dependencies on the observed SDKs**, unify A365 + OTLP + Azure Monitor exporter wiring, and manage feature flags — mirroring what the Python distro already proves out.

---

## 2. SDK OpenTelemetry Compatibility Matrix

The table below captures the current state of OpenTelemetry-native telemetry for each SDK relevant to .NET GenAI workloads.

| SDK / Library | NuGet Package | OTel-Native? | Activation Required | Telemetry Signals | Semantic Conventions | Notes |
|---|---|---|---|---|---|---|
| **Azure OpenAI SDK** | `Azure.AI.OpenAI` 2.1.0 | ✅ Yes | `AppContext.SetSwitch("OpenAI.Experimental.EnableOpenTelemetry", true)` | **Traces** (chat completions, embeddings), **Metrics** (token usage, duration) | [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) | Activity source: `OpenAI.*`. Experimental flag must be set **before** client instantiation. |
| **OpenAI .NET SDK** | `OpenAI` (transitive via Azure.AI.OpenAI) | ✅ Yes | Same `AppContext.SetSwitch` | Same as above | GenAI semconv | Azure.AI.OpenAI builds on top of the OpenAI .NET SDK; both share the same OTel pipeline. |
| **ASP.NET Core** | `OpenTelemetry.Instrumentation.AspNetCore` 1.12.0 | ✅ Yes | `.AddAspNetCoreInstrumentation()` | **Traces** (HTTP server spans), **Metrics** (request duration, active requests) | HTTP semconv | Mature, stable. Part of opentelemetry-dotnet-contrib. |
| **HttpClient** | `OpenTelemetry.Instrumentation.Http` 1.12.0 | ✅ Yes | `.AddHttpClientInstrumentation()` | **Traces** (HTTP client spans), **Metrics** (request duration) | HTTP semconv | Captures all outbound HTTP calls including Azure SDK calls. |
| **Azure Monitor** | `Azure.Monitor.OpenTelemetry.AspNetCore` 1.3.0 | ✅ Yes | `.UseAzureMonitor()` | **Traces**, **Metrics**, **Logs** + Live Metrics, Perf Counters | Azure Monitor mapping | Unified package for ASP.NET Core apps. Bundles exporter + auto-instrumentations. |
| **Microsoft Agent Framework** | `Microsoft.Agents.AI` | ✅ Yes | `.AddSource("*Microsoft.Agents.AI")` + `.UseOpenTelemetry()` on agent builder | **Traces** (agent execution, function invocation), **Metrics** (`Microsoft.Agents.AI` meter) | GenAI semconv (via `Microsoft.Extensions.AI`) | Uses `ChatClientAgent` + `IChatClient` pipeline. Agent-level and chat-client-level OTel via `.UseOpenTelemetry()`. Sensitive data opt-in via `EnableSensitiveData`. See [official sample](https://github.com/microsoft/agent-framework/blob/main/dotnet/samples/02-agents/AgentOpenTelemetry/Program.cs). |
| **Microsoft.Extensions.AI** | `Microsoft.Extensions.AI` | ✅ Yes | Via `IChatClient` pipeline + `.UseOpenTelemetry()` | **Traces** (chat completion spans, function invocations), **Metrics** (token usage) | GenAI semconv | Abstraction layer over any AI provider. `.UseOpenTelemetry(sourceName, cfg => cfg.EnableSensitiveData = true)` adds a delegating handler. This is the **key integration layer** that enables Agent Framework OTel — the OpenAI SDK `ChatClient` is converted via `.AsIChatClient()` and then wrapped. Used in our Agent Framework POC sample for full OTel coverage. |
| **Azure SDK (core)** | `Azure.Core` | ✅ Yes | Automatic (when OTel is configured) | **Traces** (HTTP pipeline spans) | Azure SDK conventions | Every Azure client (identity, storage, etc.) emits `Azure.*` activity sources automatically. Captured by `AddHttpClientInstrumentation()`. |
| **A365 Observability SDK** | `Microsoft.Agents.A365.Observability.Runtime` | ✅ Yes | `builder.AddA365Tracing(...)` | **Traces** (agent execution, A365-specific spans), custom span enrichment via `ActivityProcessor` | GenAI semconv + A365-specific attributes | Full OTel integration: `AddOpenTelemetry().WithTracing()`, `Agent365Exporter`, `ConsoleExporter` (dev), ETW via `Hosting` package. Extension packages for OpenAI, Agent Framework. Auto-sets `Azure.Experimental.EnableActivitySource` switch. |
| **LangChain (.NET)** | N/A | ❌ No | N/A | None | N/A | No official .NET LangChain library. Python/JS only. Included for cross-platform context. |

### Legend

| Symbol | Meaning |
|---|---|
| ✅ | SDK produces OpenTelemetry-compatible telemetry natively |
| ⚠️ | Partial or experimental support; requires opt-in and/or has coverage gaps |
| ❌ | No OTel telemetry emitted; requires manual instrumentation or bridge |

---

## 3. Telemetry Detail by Signal

### 3.1 Traces

| Source | Activity Source Name | Span Examples | Key Attributes |
|---|---|---|---|
| Azure OpenAI SDK | `OpenAI.*` | `chat gpt-4o` | `gen_ai.system`, `gen_ai.request.model`, `gen_ai.response.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens` |
| ASP.NET Core | `Microsoft.AspNetCore` | `POST /api/messages` | `http.method`, `http.route`, `http.status_code`, `url.path` |
| HttpClient | `System.Net.Http` | `POST https://xxx.openai.azure.com/...` | `http.method`, `server.address`, `http.response.status_code` |
| Custom (app) | `a365-agent-dotnet` / `agent-framework-dotnet-sample` | `ProcessChatRequest`, `ProcessMessage`, `ProcessUserMessage` | `user.message_length`, `assistant.message_length`, `model.deployment` |
| Agent Framework (`Agents.AI` API) | `Microsoft.Agents.AI` | Agent execution, function invocation, streaming responses | Agent name, session ID, tool calls (via `Microsoft.Extensions.AI` pipeline) |
| Microsoft.Extensions.AI | `Microsoft.Extensions.AI` | Chat completion, function invocation | `gen_ai.*` attributes via the `IChatClient` OTel middleware |
| A365 Observability SDK | A365 source name (via `OpenTelemetryConstants.SourceName`) | A365-specific agent spans, enriched via `ActivityProcessor` | A365-specific attributes, token/session metadata, exported via `Agent365Exporter` |

### 3.2 Metrics

| Source | Meter Name | Metrics | Description |
|---|---|---|---|
| Azure OpenAI SDK | `OpenAI.*` | `gen_ai.client.token.usage`, `gen_ai.client.operation.duration` | Token consumption and latency per model call |
| ASP.NET Core | `Microsoft.AspNetCore.Hosting` | `http.server.request.duration`, `http.server.active_requests` | Web server throughput and latency |
| HttpClient | `System.Net.Http` | `http.client.request.duration` | Outbound call latency |

### 3.3 Logs

All projects integrate `ILogger` → OpenTelemetry via `builder.Logging.AddOpenTelemetry()`. Logs are correlated with traces via `TraceId`/`SpanId` context propagation. No SDK-specific structured log events beyond standard .NET logging.

---

## 4. Typical .NET GenAI OTel Architecture

A .NET GenAI application wires up OpenTelemetry using standard DI patterns:

```
┌─────────────────────────────────────────────────────────────┐
│                    .NET Agent Application                    │
│                                                             │
│  1. services.AddOpenTelemetry()                             │
│     ├── .ConfigureResource(serviceName)                     │
│     ├── .WithTracing(t => {                                 │
│     │       t.AddAspNetCoreInstrumentation()                │
│     │       t.AddHttpClientInstrumentation()                │
│     │       t.AddSource("Microsoft.Agents.*")               │
│     │       t.AddSource("Microsoft.Extensions.AI")          │
│     │       t.AddSource("OpenAI.*")                         │
│     │       t.AddConsoleExporter()                          │
│     │       t.AddOtlpExporter()        // if enabled        │
│     │   })                                                  │
│     ├── .WithMetrics(m => { ... same sources ... })         │
│     └── .UseAzureMonitor()             // if conn string    │
│  2. builder.Logging.AddOpenTelemetry()                      │
│                                                             │
│  3. IChatClient pipeline (Agent Framework):                 │
│     AzureOpenAI ChatClient                                  │
│       → .AsIChatClient()                                    │
│       → .UseFunctionInvocation()                            │
│       → .UseOpenTelemetry()  ← M.E.AI spans                │
│     ChatClientAgent(chatClient, tools: [...])               │
│       → .UseOpenTelemetry()  ← Agent Framework spans        │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐ │
│  │ Console Exp. │  │  OTLP Exp.   │  │ Azure Monitor Exp.│ │
│  └──────┬───────┘  └──────┬───────┘  └────────┬──────────┘ │
└─────────┼──────────────────┼───────────────────┼────────────┘
          │                  │                   │
          ▼                  ▼                   ▼
     stdout/stderr    OTel Collector      Application Insights
                      ├── Jaeger           ├── Traces
                      └── Prometheus       ├── Metrics
                                           ├── Logs
                                           └── Live Metrics
```

**Key points:**
- Source registration uses **string patterns** (`"Microsoft.Agents.*"`, `"OpenAI.*"`) — no dependency on those SDKs
- `AppContext.SetSwitch("OpenAI.Experimental.EnableOpenTelemetry", true)` must be set before client creation
- The `IChatClient` pipeline provides layered OTel: chat-client-level spans (via `Microsoft.Extensions.AI`) and agent-level spans (via `Microsoft.Agents.AI`)
- Azure Monitor can be added via the unified `Azure.Monitor.OpenTelemetry.AspNetCore` package

---

## 5. Gap Analysis — What's Missing

### 5.1 Manual Boilerplate per Project

Each project repeats 30-70 lines of OTel configuration:

- Feature flag (`AppContext.SetSwitch`)
- Resource configuration
- Tracer provider (same 3 instrumentations + sources)
- Meter provider (same instrumentations + meters)
- Logger integration
- Conditional exporters (OTLP, Azure Monitor, Console)

### 5.2 No Standardized GenAI Attributes

Custom spans use ad-hoc attributes (`user.message_length`, `assistant.message_length`, `model.deployment`) instead of the [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) attributes like `gen_ai.request.model`, `gen_ai.usage.input_tokens`, etc. The OpenAI SDK handles this for its own spans, but application-level spans don't follow the convention.

---

## 6. Does .NET Need a Microsoft OpenTelemetry Distro?

### 6.1 The Primary Value: Convergence with A365

The A365 .NET Observability SDK (`Microsoft.Agents.A365.Observability.Runtime`) already provides `AddA365Tracing()` — a standalone OTel setup that wires the `Agent365Exporter`, span processors, and activity sources. Meanwhile, developers building .NET GenAI apps use standard `AddOpenTelemetry()` with OTLP / Azure Monitor exporters and manually register sources like `"OpenAI.*"`, `"Microsoft.Agents.*"`, `"Microsoft.Extensions.AI"`.

**These are two separate OTel pipelines solving similar problems.** A distro's primary value is unifying them:

| Without distro | With distro |
|---|---|
| `AddA365Tracing()` for A365 exporter — separate SDK, own OTel pipeline | Single `AddMicrosoftOpenTelemetry()` that wires A365 + OTLP + Azure Monitor together |
| Manual `AddOpenTelemetry().WithTracing(...)` for OTLP / Azure Monitor | Same call handles all exporters declaratively |
| Developer must know and register source strings (`"OpenAI.*"`, etc.) | Known GenAI sources registered automatically |
| `AppContext.SetSwitch` must be called before client creation — easy to forget | Distro handles feature flags automatically |
| A365 pipeline and OTLP pipeline configured independently — risk of divergent resource attributes, sampling, source lists | Single pipeline, single configuration, consistent behavior |

Instead of teams combining `AddA365Tracing()` with their own OTel setup (potentially getting different resource names, different source registrations, different sampling strategies), the distro provides one unified entry point.

### 6.2 Secondary Benefits

- **Cross-language consistency** — Teams running Python + .NET agents get the same env vars (`ENABLE_OTLP_EXPORTER`, `APPLICATIONINSIGHTS_CONNECTION_STRING`), same parameter names, same behavior
- **Enterprise standardization** — "Golden path" config for many teams, prevents drift and misconfigurations
- **Guardrails** — No need to learn `WithTracing` vs `WithMetrics` vs `AddOpenTelemetry` on logging; a validated default reduces subtle misconfigurations

### 6.3 What the Distro is NOT

The distro is a **pipeline configurator, not a capability enabler**. The SDKs (OpenAI, Agent Framework, `Microsoft.Extensions.AI`, A365 Observability) already produce OTel telemetry natively. The distro:

- Depends **only** on OTel SDK + exporter packages — never on `Microsoft.Agents.AI`, `Azure.AI.OpenAI`, or any AI SDK
- Registers activity sources as **string patterns** (`"OpenAI.*"`, `"Microsoft.Agents.*"`) — zero assembly references
- Configures the collection pipeline (providers, exporters, resource attributes, sampling)

### 6.4 Proposed API

```csharp
builder.Services.AddMicrosoftOpenTelemetry(options =>
{
    options.ServiceName = "my-agent";
    options.EnableGenAI = true;               // registers known GenAI source patterns (strings only)
    options.EnableOtlpExport = true;          // OTLP exporter
    options.AzureMonitorConnectionString = connectionString;
    options.EnableA365Export = true;           // A365 exporter (wraps existing A365 Observability SDK)
    options.A365TokenResolver = tokenResolver;
});
```

### 6.5 Value by Scenario

| Scenario | Value | Why |
|---|---|---|
| **A365-deployed agents needing OTLP/Azure Monitor too** | **High** | Unifies A365 exporter with OTLP + Azure Monitor in one pipeline — the core convergence story |
| **Team running Python + .NET agents** | **High** | Cross-language consistency in config, env vars, and behavior |
| **Enterprise with many teams** | **High** | Standardized "golden path" prevents drift and misconfigurations |
| **Greenfield .NET GenAI app** | Moderate | Saves boilerplate, auto-registers sources |
| **Single .NET app, Azure Monitor only** | Low | `Azure.Monitor.OpenTelemetry.AspNetCore` already does everything needed |
| **Single .NET app, OTLP only** | Low | Standard OTel setup is ~30 lines, well-documented, idiomatic |

---
## 7. Exporter & Backend Topology

### Local Development (Docker Compose)

```
.NET Agent (localhost:5109)
  │
  ├── OTLP HTTP (:4318) ──→ OTel Collector (contrib 0.120.0)
  │                            ├──→ Jaeger (:16686) — trace visualization
  │                            └──→ Prometheus (:9090) — metrics dashboard
  │
  └── Console ──→ stdout (always on)
```

### Production (Azure)

```
.NET Agent (App Service / AKS)
  │
  ├── Azure Monitor Exporter ──→ Application Insights
  │                                ├── Transaction Search (traces)
  │                                ├── Metrics Explorer
  │                                ├── Log Analytics (KQL)
  │                                └── Live Metrics Stream
  │
  └── OTLP (optional) ──→ Any OTel-compatible backend
```

---

## 8. OpenAI SDK Telemetry Deep Dive

The `Azure.AI.OpenAI` / `OpenAI` .NET SDK produces the richest native telemetry in this stack. Key details:

### Activation

```csharp
// MUST be called before any OpenAI client is created
AppContext.SetSwitch("OpenAI.Experimental.EnableOpenTelemetry", true);
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
| `server.port` | `443` | Endpoint port |

### Metrics

| Metric | Type | Unit | Description |
|---|---|---|---|
| `gen_ai.client.token.usage` | Histogram | `token` | Token count per request (input + output) |
| `gen_ai.client.operation.duration` | Histogram | `s` | End-to-end call duration |

### Content Capture

By default, prompt and completion content is **not** included in spans (privacy). To enable:

```csharp
AppContext.SetSwitch("OpenAI.Experimental.EnableOpenTelemetry", true);
// Content is controlled by the OTel spec — currently not exposed in the .NET SDK
```

---

## 9. Recommendations

### Short-term (POC next steps)

1. **~~Migrate Agent Framework POC to `ChatClientAgent` + `Microsoft.Extensions.AI`~~** — ✅ Done. The POC now uses `ChatClientAgent` with `Microsoft.Agents.AI` 1.0.0-rc4, `Microsoft.Extensions.AI.OpenAI` 10.4.1, and `.UseOpenTelemetry()` at both the `IChatClient` and agent levels.
2. **Standardize custom span attributes** — Align remaining app-level spans with GenAI semantic conventions instead of ad-hoc names.
3. **Add multi-turn session management** — The current `/api/chat` endpoint creates a new session per request. Adding session persistence would demonstrate how `ChatClientAgent` sessions carry conversation history with full trace correlation.

### Medium-term (Distro development)

4. **Build .NET distro NuGet package** — `Microsoft.OpenTelemetry` with `AddMicrosoftOpenTelemetry()` extension that auto-registers all known GenAI sources (`OpenAI.*`, `Microsoft.Agents.*`, `Microsoft.Extensions.AI`).
5. **Auto-detect AI pipeline** — The distro should detect whether `Microsoft.Extensions.AI` types are in use and ensure `.UseOpenTelemetry()` is part of the pipeline.
6. **Environment-variable parity** — Support same env vars across Python and .NET distros for consistency.

### Long-term (Ecosystem)

7. **Older API (`AgentApplication`) bridge instrumentation** — For users who cannot migrate to `ChatClientAgent`, provide a bridge instrumentor that wraps turn processing in spans.
8. **Feature parity across languages** — .NET, Python, and JS distros expose the same capabilities.

---

## 10. Package Reference Summary

### Common across all .NET projects

| Package | Version | Role |
|---|---|---|
| `Azure.AI.OpenAI` | 2.1.0 | Azure OpenAI client (wraps `OpenAI` SDK) |
| `Azure.Identity` | 1.13.2 – 1.17.1 | `DefaultAzureCredential` for token-based auth |
| `OpenTelemetry.Exporter.Console` | 1.10.0 | Console trace/metric/log output |
| `OpenTelemetry.Exporter.OpenTelemetryProtocol` | 1.10.0 – 1.12.0 | OTLP gRPC/HTTP exporter |

### Web projects only (A365 Agent, Agent Framework)

| Package | Version | Role |
|---|---|---|
| `Azure.Monitor.OpenTelemetry.AspNetCore` | 1.3.0 | Unified Azure Monitor exporter + auto-instrumentation |
| `OpenTelemetry.Extensions.Hosting` | 1.12.0 | `IServiceCollection` DI integration |
| `OpenTelemetry.Instrumentation.AspNetCore` | 1.12.0 | HTTP server spans & metrics |
| `OpenTelemetry.Instrumentation.Http` | 1.12.0 | HTTP client spans & metrics |

### Agent Framework only

| Package | Version | Role |
|---|---|---|
| `Microsoft.Agents.AI` | 1.0.0-rc4 | Agent Framework core — `ChatClientAgent`, agent builder, `.UseOpenTelemetry()` |
| `Microsoft.Agents.AI.OpenAI` | 1.0.0-rc4 | OpenAI-specific agent integration |
| `Microsoft.Extensions.AI.OpenAI` | 10.4.1 | `IChatClient` abstraction for OpenAI — `.AsIChatClient()`, `.UseOpenTelemetry()`, `.UseFunctionInvocation()` |

### Console app only (Azure OpenAI)

| Package | Version | Role |
|---|---|---|
| `Azure.Monitor.OpenTelemetry.Exporter` | 1.3.0 | Standalone Azure Monitor exporter (no ASP.NET dependency) |
| `OpenTelemetry` | 1.10.0 | Core SDK for manual provider setup |
| `Microsoft.Extensions.Configuration.EnvironmentVariables` | 8.0.0 | Env var config source |
