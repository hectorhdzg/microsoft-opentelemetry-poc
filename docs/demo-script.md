# Demo Script — Microsoft OpenTelemetry Distro

> **Format:** Each scene has narration text optimized for **Clipchamp text-to-speech**.
> Each numbered line is a **separate TTS clip**. Drop them onto the timeline and
> add silent gaps between clips to create pauses.
> Commas and periods within a clip provide natural micro-pauses.
>
> **Structure:** ~1 min problem & solution, ~1 min live telemetry across all backends.

---

## Part 1 — The Problem & The Solution (~1 min)

### Scene 1 — The Current Issue

**Visual:** Title slide — "Observability for AI Agents Today" → transition to logos of Azure Monitor, A365, OTLP, OpenAI, LangChain appearing separately across the screen

**Clips:**

1. Today, observability for AI agents on Microsoft's platform is fragmented. Azure Monitor has its own SDK. Agent 365 has a completely separate observability stack. And OTLP, OpenAI, and LangChain each come with different instrumentation packages and different onboarding paths.
2. Developers have to discover, install, and wire together pieces from multiple product teams just to get traces flowing. And internally, each team is solving the same problems independently, duplicating effort across the organization.

### Scene 2 — The Proposal

**Visual:** Title slide — "Microsoft OpenTelemetry Distro" → architecture diagram showing one package connecting to Azure Monitor, A365, and OTLP

**Clips:**

1. The proposal is a single Microsoft OpenTelemetry distribution, one package that handles all of this. Azure Monitor, Agent 365, and OTLP export, all configured through one function call. Instead of four separate SDKs, developers get one onboarding experience.
2. It also handles instrumentations. Agent Framework, OpenAI, LangChain. The distro wires them up automatically. Less code for developers, less duplication across teams.

### Scene 3 — What It Looks Like in Code

**Visual:** Full screen `src/microsoft_distro_observability_config.py` → zoom into the `configure_microsoft_opentelemetry()` call and its parameters

**Clips:**

1. Here's what the distro approach looks like. One import, one function call. You pass in which exporters and instrumentations you want, and the distro handles the rest. No manual provider setup, no separate instrumentor initialization.
2. Compare that to the manual approach, where you'd need separate SDK calls for A365, Azure Monitor, Agent Framework, OpenAI, and LangChain, each with its own imports and error handling.

---

## Part 2 — Live Telemetry Demo (~1 min)

### Scene 4 — Playground Calling the Agent

**Visual:** Open M365 Agents Playground → connect to `http://localhost:3978/api/messages` → send a message to the agent → show the agent responding

**Clips:**

1. Here's the agent running locally. We're using the M365 Agents Playground to send a message. The agent processes the request using Azure OpenAI, and we get a response back. Now let's look at the telemetry that was generated across all our backends.

### Scene 5 — Azure Monitor: Traces, Metrics, Logs & Live Metrics

**Visual:** Switch to Azure Portal → Application Insights → Transaction search showing traces → drill into a trace to show spans → switch to Metrics blade → switch to Logs blade → switch to Live Metrics view showing real-time data

**Clips:**

1. In Application Insights, we can see the full trace. The request, the agent processing, and the OpenAI calls, all with model names, token counts, and latency. We also have metrics, showing request rates and dependencies. And logs, captured alongside the traces.
2. Here's Live Metrics. As we send more messages through the Playground, we can watch requests, failures, and dependencies update in real time. All of this came from the same single function call in the distro configuration.

### Scene 6 — OTLP: Jaeger Traces & Prometheus Metrics

**Visual:** Switch to terminal showing `docker compose -f docker/docker-compose.yml up -d` → open browser to Jaeger UI at `http://localhost:16686` → search for traces → drill into a trace → switch to Prometheus UI showing metrics

**Clips:**

1. In parallel, the distro is also exporting to OTLP. We're running the OpenTelemetry Collector in Docker. In Jaeger, we can see the same traces, the same span hierarchy, the agent request flowing through OpenAI. And in Prometheus, we can query the metrics that the collector is exposing.

### Scene 7 — Console Exporter

**Visual:** Switch back to terminal where the agent is running → scroll to show console output with trace and span data printed in real time

**Clips:**

1. For local debugging, the console exporter prints trace data directly in the terminal. You can see span names, durations, attributes, and the parent-child relationships. No external tools needed, just run the agent and read the output.

### Scene 8 — A365 Telemetry

**Visual:** Switch to A365 telemetry view → show enriched spans with normalized attributes → highlight A365-specific metadata like agent ID and tenant ID

**Clips:**

1. Finally, Agent 365 telemetry. The same spans appear here with enriched attributes, normalized naming, agent ID, and tenant ID. The A365 instrumentors bridge the agent framework, OpenAI, and LangChain traces into the A365 observability pipeline. All three backends, one function call.

---

## Closing

**Visual:** Back to the editor showing the `configure_microsoft_opentelemetry()` call → fade to title slide — "One Package. One Onboarding. Every Backend."

**Clips:**

1. One distro. Azure Monitor with traces, metrics, logs, and live metrics. All from a single function call. Less confusion for developers, less duplication across teams.

---

## Timing Estimates

| Scene | Clips | Approx. Duration |
|-------|-------|-------------------|
| 1 — The Current Issue | 2 | ~20 sec |
| 2 — The Proposal | 2 | ~15 sec |
| 3 — What It Looks Like in Code | 2 | ~20 sec |
| 4 — Playground Calling the Agent | 1 | ~10 sec |
| 5 — Azure Monitor (traces, metrics, logs, live metrics) | 2 | ~20 sec |
| 6 — OTLP (Jaeger + Prometheus) | 1 | ~15 sec |
| 7 — Console Exporter | 1 | ~10 sec |
| 8 — A365 Telemetry | 1 | ~10 sec |
| Closing | 1 | ~10 sec |
| **Total** | **13** | **~2.5 min** |
