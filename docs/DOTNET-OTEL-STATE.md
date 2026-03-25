# .NET OpenTelemetry & GenAI Instrumentation — Current State

> **Scope:** .NET ecosystem — Azure OpenAI SDK, Microsoft Agent Framework, A365 Agent, and how they integrate with OpenTelemetry today. Includes an assessment of where a **Microsoft OpenTelemetry SDK (distro)** adds value.

---

## 1. Executive Summary

The .NET GenAI stack has strong—but fragmented—OpenTelemetry support. The **Azure OpenAI SDK** ships native OTel spans behind an experimental feature flag, **Microsoft Agent Framework** supports OTel via `Microsoft.Extensions.AI` integration and its own `Microsoft.Agents.AI` activity sources, ASP.NET Core and HttpClient have mature community instrumentations, and Azure Monitor provides a unified exporter. However, each project must still wire up **30-70 lines of boilerplate** to configure providers, exporters, sources, and feature flags, and the level of OTel support varies significantly by which API surface is used.

A **Microsoft OpenTelemetry .NET Distro** would collapse this setup into a single `.AddMicrosoftOpenTelemetry()` call, auto-register GenAI sources (including `Microsoft.Agents.AI`), and ensure consistent instrumentation regardless of which Agent Framework API surface is used — mirroring what the Python distro already proves out.

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
| **Microsoft Agent Framework** (newer `Agents.AI` API) | `Microsoft.Agents.AI` | ✅ Yes | `.AddSource("*Microsoft.Agents.AI")` + `.UseOpenTelemetry()` on agent builder | **Traces** (agent execution, function invocation), **Metrics** (`Microsoft.Agents.AI` meter) | GenAI semconv (via `Microsoft.Extensions.AI`) | Uses `ChatClientAgent` + `IChatClient` pipeline. Agent-level and chat-client-level OTel via `.UseOpenTelemetry()`. Sensitive data opt-in via `EnableSensitiveData`. See [official sample](https://github.com/microsoft/agent-framework/blob/main/dotnet/samples/02-agents/AgentOpenTelemetry/Program.cs). |
| **Microsoft Agent Framework** (older `Agents.Builder` API) | `Microsoft.Agents.Hosting.AspNetCore` 1.5.76-beta | ❌ No | N/A | None (no spans or metrics emitted) | N/A | `AgentApplication` base class + `OnActivity()` handlers. Activity pipeline, turn state, and Bot Framework connector calls are **not instrumented**. Requires manual `ActivitySource` spans. Legacy API — avoid for new projects. |
| **Microsoft.Extensions.AI** | `Microsoft.Extensions.AI` | ✅ Yes | Via `IChatClient` pipeline + `.UseOpenTelemetry()` | **Traces** (chat completion spans, function invocations), **Metrics** (token usage) | GenAI semconv | Abstraction layer over any AI provider. `.UseOpenTelemetry(sourceName, cfg => cfg.EnableSensitiveData = true)` adds a delegating handler. This is the **key integration layer** that enables Agent Framework OTel — the OpenAI SDK `ChatClient` is converted via `.AsIChatClient()` and then wrapped. Used in our Agent Framework POC sample for full OTel coverage. |
| **Azure SDK (core)** | `Azure.Core` | ✅ Yes | Automatic (when OTel is configured) | **Traces** (HTTP pipeline spans) | Azure SDK conventions | Every Azure client (identity, storage, etc.) emits `Azure.*` activity sources automatically. Captured by `AddHttpClientInstrumentation()`. |
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

### 3.2 Metrics

| Source | Meter Name | Metrics | Description |
|---|---|---|---|
| Azure OpenAI SDK | `OpenAI.*` | `gen_ai.client.token.usage`, `gen_ai.client.operation.duration` | Token consumption and latency per model call |
| ASP.NET Core | `Microsoft.AspNetCore.Hosting` | `http.server.request.duration`, `http.server.active_requests` | Web server throughput and latency |
| HttpClient | `System.Net.Http` | `http.client.request.duration` | Outbound call latency |

### 3.3 Logs

All projects integrate `ILogger` → OpenTelemetry via `builder.Logging.AddOpenTelemetry()`. Logs are correlated with traces via `TraceId`/`SpanId` context propagation. No SDK-specific structured log events beyond standard .NET logging.

---

## 4. Current Integration Architecture

The three .NET POC projects share a common instrumentation pattern:

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
│  3. IChatClient pipeline (Agent Framework sample):          │
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

### Per-Project Differences

| Aspect | Azure OpenAI (Console) | A365 Agent (Web) | Agent Framework (Web) |
|---|---|---|---|
| Host model | Standalone `Sdk.CreateTracerProviderBuilder()` | `IServiceCollection.AddOpenTelemetry()` | `IServiceCollection.AddOpenTelemetry()` |
| ASP.NET instrumentation | N/A (console app) | ✅ | ✅ |
| HttpClient instrumentation | N/A | ✅ | ✅ |
| Agent Framework API | N/A | N/A | `ChatClientAgent` + `IChatClient` pipeline via `Microsoft.Agents.AI` 1.0.0-rc4 |
| OTel at AI layer | `AppContext.SetSwitch` (OpenAI SDK native) | `AppContext.SetSwitch` (OpenAI SDK native) | `.UseOpenTelemetry()` on both `IChatClient` and `ChatClientAgent` — native spans from `Microsoft.Agents.AI` + `Microsoft.Extensions.AI` |
| Azure Monitor package | `Azure.Monitor.OpenTelemetry.Exporter` (manual) | `Azure.Monitor.OpenTelemetry.AspNetCore` (unified) | `Azure.Monitor.OpenTelemetry.AspNetCore` (unified) |
| Custom spans | `ProcessUserMessage` | `ProcessMessage`, `Agent.ProcessMessage` | `ProcessChatRequest` |

---

## 5. Gap Analysis — What's Missing

### 5.1 Agent Framework: Two API Surfaces, Two OTel Stories

The Microsoft Agent Framework has **two distinct API surfaces** with very different OTel capabilities:

#### Newer API: `Microsoft.Agents.AI` + `Microsoft.Extensions.AI` — ✅ OTel-enabled

The [official OpenTelemetry sample](https://github.com/microsoft/agent-framework/blob/main/dotnet/samples/02-agents/AgentOpenTelemetry/Program.cs) demonstrates full OTel integration using the newer `ChatClientAgent` API:

```csharp
// Convert OpenAI SDK ChatClient → IChatClient with OTel pipeline
var instrumentedChatClient = new AzureOpenAIClient(new Uri(endpoint), new DefaultAzureCredential())
    .GetChatClient(deploymentName)
    .AsIChatClient()                                         // → IChatClient
    .AsBuilder()
    .UseFunctionInvocation()                                 // tool calling
    .UseOpenTelemetry(sourceName: SourceName,                // OTel at chat client level
        configure: cfg => cfg.EnableSensitiveData = true)
    .Build();

// Create agent with OTel at the agent level
var agent = new ChatClientAgent(instrumentedChatClient,
    name: "OpenTelemetryDemoAgent",
    instructions: "You are a helpful assistant.",
    tools: [AIFunctionFactory.Create(GetWeatherAsync)])
    .AsBuilder()
    .UseOpenTelemetry(SourceName,                            // OTel at agent level
        configure: cfg => cfg.EnableSensitiveData = true)
    .Build();
```

**Telemetry produced:**
- Activity source: `Microsoft.Agents.AI` — registered via `.AddSource("*Microsoft.Agents.AI")`
- Meter: `Microsoft.Agents.AI` — registered via `.AddMeter("*Microsoft.Agents.AI")`
- Agent execution spans, function invocation spans, streaming response spans
- Full trace correlation from HTTP → agent → AI model → tool calls

#### Older API: `Microsoft.Agents.Builder` (`AgentApplication`) — ❌ No OTel

The older `AgentApplication` + `OnActivity()` pattern has **no built-in OTel**. Under this API, agent-level operations (activity routing, turn processing, state management, Bot Framework connector) are invisible in traces.

With the older API, a trace looks like:

```
[ASP.NET: POST /api/messages]
  └── [HttpClient: POST openai.azure.com/...]
        └── [OpenAI SDK: chat gpt-4o]
```

With the **newer API** (used in our POC), the same request produces:

```
[ASP.NET: POST /api/chat]
  └── [ProcessChatRequest]                          ← custom app span
        └── [Microsoft.Agents.AI: Agent Execution]
              ├── [Microsoft.Extensions.AI: Chat Completion]
              │     └── [OpenAI SDK: chat gpt-4o]
              └── [Microsoft.Extensions.AI: Function Invocation]
                    └── [GetWeatherAsync]
```

**Our POC uses the newer `ChatClientAgent` API**, demonstrating full native OTel support with no bridge instrumentation needed.

### 5.2 Manual Boilerplate per Project

Each project repeats 30-70 lines of OTel configuration:

- Feature flag (`AppContext.SetSwitch`)
- Resource configuration
- Tracer provider (same 3 instrumentations + sources)
- Meter provider (same instrumentations + meters)
- Logger integration
- Conditional exporters (OTLP, Azure Monitor, Console)

### 5.3 No Standardized GenAI Attributes

Custom spans use ad-hoc attributes (`user.message_length`, `assistant.message_length`, `model.deployment`) instead of the [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) attributes like `gen_ai.request.model`, `gen_ai.usage.input_tokens`, etc. The OpenAI SDK handles this for its own spans, but application-level spans don't follow the convention.

---

## 6. Does .NET Need a Microsoft OpenTelemetry Distro?

### 6.1 The Honest Assessment: .NET Already Covers Most of the Ground

Unlike Python — where the distro consolidates a fragmented ecosystem of community instrumentations, manual provider setup, and missing bridge libraries — the .NET ecosystem is **already well-integrated through first-party SDKs**:

| Capability | .NET Native Solution | Python (requires distro) |
|---|---|---|
| **OTel provider setup** | `builder.Services.AddOpenTelemetry()` — built into `Microsoft.Extensions.Hosting` | Manual `TracerProvider` / `MeterProvider` / `LoggerProvider` construction |
| **Web framework instrumentation** | Single `AddAspNetCoreInstrumentation()` covers all ASP.NET Core apps | Separate packages for Django, FastAPI, Flask — each must be activated individually |
| **GenAI (OpenAI) telemetry** | Native in OpenAI .NET SDK via `AppContext.SetSwitch` | Requires community `opentelemetry-instrumentation-openai-v2` package |
| **Agent Framework telemetry** | Native via `ChatClientAgent` + `.UseOpenTelemetry()` | Requires A365-specific bridge instrumentor |
| **AI abstraction layer** | `Microsoft.Extensions.AI` with `.UseOpenTelemetry()` built-in | No equivalent — each library instrumented separately |
| **Azure Monitor export** | `Azure.Monitor.OpenTelemetry.AspNetCore` — single package, bundles everything | `azure-monitor-opentelemetry` — similar, but distro adds value by unifying with OTLP + A365 |
| **DI / builder pattern** | First-class via `IServiceCollection` extensions | Not native to Python — distro fills this gap |

**In short:** The Python distro replaces ~250 lines of scattered setup with a single call. In .NET, the "before" is already only ~30-50 lines of clean, idiomatic code using standard DI patterns. The marginal value of collapsing 40 lines into 5 is much lower.

### 6.2 Where a .NET Distro *Would* Still Add Value

Despite the strong native support, there are real gaps a distro could fill. Critically, any distro must follow the **core OTel philosophy**: SDK authors are responsible for producing their own telemetry; the distro only configures the *collection pipeline* (providers, exporters, resource attributes, source registration). **The distro must never depend on the SDKs it observes.**

This is exactly what makes .NET's situation favorable: Agent Framework, OpenAI SDK, and `Microsoft.Extensions.AI` all already produce OTel-native telemetry. The distro just needs to make sure the pipeline is listening.

#### ① A365 Exporter (does not exist in .NET today)

The Python distro includes A365-specific export — `EnrichingBatchSpanProcessor` → `Agent365Exporter` — with token resolvers, cluster categories, and span enrichment. **There is no .NET equivalent.** If A365 export is a requirement, a distro or standalone package is the only way to get it.

#### ② Source Registration (strings only — zero SDK dependencies)

Developers must currently discover and register the correct activity source and meter names:

```csharp
// You have to know these exist and spell them correctly
.AddSource("Microsoft.Agents.*")
.AddSource("Microsoft.Extensions.AI")
.AddSource("OpenAI.*")
.AddMeter("Microsoft.Agents.*")
.AddMeter("Microsoft.Extensions.AI")
.AddMeter("OpenAI.*")
```

A distro could register all known GenAI sources automatically. These are just strings passed to `.AddSource()` / `.AddMeter()` — **no NuGet dependency on any AI SDK is needed**. The distro registers wildcard patterns like `"Microsoft.Agents.*"` and `"OpenAI.*"`; if the user's app happens to use those SDKs, spans flow through. If not, the patterns are harmless no-ops.

This is the correct architecture — the distro depends only on OpenTelemetry packages and exporter packages, never on `Microsoft.Agents.AI`, `Azure.AI.OpenAI`, or any other SDK that produces telemetry. Those SDKs bring their own `ActivitySource` / `Meter` instances; the distro just ensures the pipeline is configured to collect them.

#### ③ Feature Flag Management

The OpenAI SDK requires `AppContext.SetSwitch("OpenAI.Experimental.EnableOpenTelemetry", true)` *before* any client is created. Easy to forget, impossible to debug when missed. A distro would handle this automatically.

#### ④ Cross-Language Consistency

Enterprise teams running Python agents alongside .NET agents benefit from a single configuration model. Same env vars (`ENABLE_OTLP_EXPORTER`, `APPLICATIONINSIGHTS_CONNECTION_STRING`), same parameter names, same behavior — regardless of runtime.

#### ⑤ Multi-Exporter Wiring

The conditional `if (enableOtlp)` / `if (!string.IsNullOrEmpty(azMonConnectionString))` pattern is repeated in every project. A distro makes this declarative.

#### ⑥ Guardrails for New Teams

Teams new to OTel don't need to learn `WithTracing` vs `WithMetrics` vs `AddOpenTelemetry` on logging. A validated default configuration reduces the probability of subtle misconfigurations (e.g., forgetting to register a source, missing the feature flag, not correlating logs with traces).

### 6.3 Proposed API (if built)

```csharp
// The distro depends ONLY on OTel SDK + exporter packages.
// No dependency on Azure.AI.OpenAI, Microsoft.Agents.AI, or any AI SDK.
// It just configures the pipeline — the SDKs produce their own telemetry.
builder.Services.AddMicrosoftOpenTelemetry(options =>
{
    options.ServiceName = "my-agent";
    options.EnableGenAI = true;               // registers known GenAI source patterns (strings only)
    options.EnableOtlpExport = true;          // OTLP exporter
    options.AzureMonitorConnectionString = connectionString;
    options.EnableA365Export = true;           // A365 exporter (the big gap)
    options.A365TokenResolver = tokenResolver;
});

// Under the hood, EnableGenAI = true does:
//   .AddSource("OpenAI.*")
//   .AddSource("Microsoft.Agents.*")
//   .AddSource("Microsoft.Extensions.AI")
//   .AddMeter("OpenAI.*")
//   .AddMeter("Microsoft.Agents.*")
//   .AddMeter("Microsoft.Extensions.AI")
// These are just string patterns — no assembly references.
```

### 6.4 Value Assessment by Scenario

| Scenario | Distro Value | Why |
|---|---|---|
| **Greenfield .NET GenAI app** | 🟡 Moderate | Saves 30-40 lines of boilerplate, auto-registers sources. Nice-to-have, not essential. |
| **Team running Python + .NET agents** | 🟢 High | Cross-language consistency in config, env vars, and behavior. |
| **A365-deployed agents** | 🟢 High | A365 exporter only available through distro. No .NET alternative exists. |
| **Enterprise with many teams** | 🟢 High | Standardized "golden path" config prevents drift and misconfigurations. |
| **Single .NET app, Azure Monitor only** | 🔴 Low | `Azure.Monitor.OpenTelemetry.AspNetCore` already does everything needed. |
| **Single .NET app, OTLP + Jaeger** | 🔴 Low | Standard OTel setup is ~30 lines, well-documented, idiomatic. |

### 6.5 Bottom Line

**The .NET distro is a pipeline configurator, not a capability enabler.** The SDKs (OpenAI, Agent Framework, `Microsoft.Extensions.AI`) already produce OTel telemetry natively — that's the whole point of OpenTelemetry. The distro's job is to configure the collection pipeline (providers, exporters, source registration) without depending on any of those SDKs.

The distro's strongest justifications are:

1. **A365 export** — genuinely missing in .NET, no alternative exists
2. **Cross-language teams** — single config model across Python/.NET/JS
3. **Enterprise standardization** — "golden path" for many teams, prevents config drift
4. **Source registration** — maintain a known list of GenAI activity source patterns so developers don't have to discover magic strings

For a single team building one .NET agent with Azure Monitor or OTLP, the native SDK integrations are sufficient and idiomatic. The distro becomes compelling when you add A365 requirements, multi-language deployments, or organizational scale.

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
