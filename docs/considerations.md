# Considerations

Key design considerations, trade-offs, and open questions for the `microsoft-opentelemetry` distro.

---

## Package Size & Dependencies

The distro wheel itself is small (~19 KB), but it pulls in a significant dependency tree:

| Category | Packages | Notes |
|----------|----------|-------|
| **OpenTelemetry SDK** | `opentelemetry-sdk ~=1.39`, `opentelemetry-resource-detector-azure` | Core OTel runtime |
| **Azure Monitor** | `azure-monitor-opentelemetry ~=1.6.0` | Brings in Application Insights exporter, live metrics, perf counters |
| **OTLP Exporters** | `opentelemetry-exporter-otlp-proto-http ~=1.39` | HTTP/protobuf by default; gRPC via `[otlp-grpc]` extra |
| **Web Instrumentations** (7) | Django, FastAPI, Flask, psycopg2, requests, urllib, urllib3 | All installed regardless of which framework is used |
| **GenAI Instrumentations** (3) | `opentelemetry-instrumentation-openai-v2`, `-openai-agents`, `-langchain` | Community contrib packages |
| **A365 Observability** (4) | `microsoft-agents-a365-observability-core`, extensions for OpenAI, LangChain, Agent Framework | A365-specific span enrichment and bridging |

**Total transitive dependency count is high.** Developers who only need Azure Monitor + one framework (e.g. FastAPI) still get Django, Flask, psycopg2, LangChain instrumentation packages installed.

### Open Questions

- Should web/GenAI/A365 instrumentations be optional extras instead of hard dependencies (e.g. `pip install microsoft-opentelemetry[fastapi,openai]`)?
- What is the total installed size including all transitive dependencies?
- How does cold-start / import time scale with the full dependency tree (relevant for serverless)?

---

## Python Version Support

The distro supports **Python 3.9 – 3.13** (per `setup.py` classifiers). This POC project requires **Python ≥ 3.11** due to Agent Framework SDK constraints.

---

## Multi-Language Support

The current prototype is **Python-only**. For the distro to serve as the unified Microsoft observability story, equivalent packages are needed for other languages.

### JavaScript / TypeScript

- Azure Monitor already has [`@azure/monitor-opentelemetry`](https://www.npmjs.com/package/@azure/monitor-opentelemetry) for Node.js
- A365 has an existing Node.js SDK: [`Agent365-nodejs`](https://github.com/microsoft/Agent365-nodejs)
- OpenTelemetry JS ecosystem is mature — instrumentations for Express, Fastify, etc. already exist
- A `microsoft-opentelemetry` npm package could follow the same single-call pattern

### .NET

- Azure Monitor has [`Azure.Monitor.OpenTelemetry.AspNetCore`](https://www.nuget.org/packages/Azure.Monitor.OpenTelemetry.AspNetCore) and [`Azure.Monitor.OpenTelemetry.Exporter`](https://www.nuget.org/packages/Azure.Monitor.OpenTelemetry.Exporter)
- A365 has an existing .NET SDK: [`Agent365-dotnet`](https://github.com/microsoft/Agent365-dotnet)
- .NET has first-class OpenTelemetry support via `Microsoft.Extensions.Hosting` and `IServiceCollection` extensions
- A .NET distro could use the builder pattern: `services.AddMicrosoftOpenTelemetry(o => { o.EnableA365Export = true; })`

### Considerations for Multi-Language

- API surface should be consistent across languages (same parameter names, same env var support)
- Each language has its own OpenTelemetry SDK maturity level and idioms — the distro should follow platform conventions
- A365 SDKs already exist for all three languages: [Python](https://github.com/microsoft/Agent365-python) (observability extensions used in this POC), [Node.js](https://github.com/microsoft/Agent365-nodejs), and [.NET](https://github.com/microsoft/Agent365-dotnet) — the distro needs to integrate with each
- Feature parity timeline and prioritization across languages is an open question

---

## Feature Gating

Currently, all instrumentations are installed but disabled by default (opt-in via boolean flags or env vars). Two alternative models:

| Model | Pros | Cons |
|-------|------|------|
| **Current: all installed, opt-in enable** | Simple install, no extras to manage | Large dependency footprint |
| **Extras-based: `pip install microsoft-opentelemetry[a365,openai]`** | Smaller installs, only pull what you need | More complex install commands, potential confusion |
| **Auto-detect: enable if library is importable** | Zero config for common cases | Implicit behavior can surprise, harder to debug |

---

## Versioning & Release Cadence

- The distro depends on pinned ranges of OpenTelemetry SDK (`~=1.39`), Azure Monitor (`~=1.6.0`), and A365 packages (`>=0.2.0`)
- OpenTelemetry Python ships monthly — the distro must keep pace to avoid version conflicts
- Azure Monitor and A365 SDK releases are independent — coordinating compatible version sets is an ongoing concern
- Currently at `0.1.0b1` (beta) — stability guarantees and breaking change policy need to be defined before GA
