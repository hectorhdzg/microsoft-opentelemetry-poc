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

### Scene 2 — The Proposed Solution

**Visual:** Split screen — left: `src/observability_config.py` scrolling through ~170 lines → right: `src/microsoft_distro_observability_config.py` showing ~56 lines. Zoom into the `configure_microsoft_opentelemetry()` call.

**Clips:**

1. On the left is the manual approach. About 170 lines. Multiple SDKs, multiple instrumentors, each wired separately. On the right is the same agent using the Microsoft OpenTelemetry Distro. About 56 lines. One function call that configures all exporters and instrumentations together.
2. Azure Monitor, A365, OTLP, Agent Framework, OpenAI, LangChain. All configured through a single function. One package, one onboarding experience, instead of four.

---

## Part 2 — Live Telemetry Demo (~1 min)

### Scene 3 — Playground Calling the Agent

**Visual:** Open M365 Agents Playground → connect to `http://localhost:3978/api/messages` → send a message to the agent → show the agent responding

**Clips:**

1. Here's the agent running locally. We're using the M365 Agents Playground to send a message. The agent processes the request using Azure OpenAI, and we get a response back. Now let's look at the telemetry that was generated across all our backends.

### Scene 4 — Azure Monitor: Traces, Metrics, Logs & Live Metrics

**Visual:** Switch to Azure Portal → Application Insights → Transaction search showing traces → drill into a trace to show spans → switch to Metrics blade → switch to Logs blade → switch to Live Metrics view showing real-time data

**Clips:**

1. In Application Insights, we can see the full trace. The incoming request, the agent processing, and the OpenAI calls, all with model names, token counts, and latency. We also have metrics, showing request rates and dependencies. And logs, captured alongside the traces.
2. Here's Live Metrics. As we send more messages through the Playground, we can watch requests, failures, and dependencies update in real time. All of this came from the same single function call in the distro configuration.

### Scene 5 — OTLP: Jaeger Traces & Prometheus Metrics

**Visual:** Switch to terminal showing `docker compose -f docker/docker-compose.yml up -d` → open browser to Jaeger UI at `http://localhost:16686` → search for traces → drill into a trace → switch to Prometheus UI showing metrics

**Clips:**

1. In parallel, the distro is also exporting to OTLP. We're running the OpenTelemetry Collector in Docker. In Jaeger, we can see the same traces, the same span hierarchy, the agent request flowing through OpenAI. And in Prometheus, we can query the metrics that the collector is exposing.

### Scene 6 — Console Exporter

**Visual:** Switch back to terminal where the agent is running → scroll to show console output with trace and span data printed in real time

**Clips:**

1. For local debugging, the console exporter prints trace data directly in the terminal. You can see span names, durations, attributes, and the parent-child relationships. No external tools needed, just run the agent and read the output.

### Scene 7 — A365 Telemetry

**Visual:** Switch to A365 telemetry view → show enriched spans with normalized attributes → highlight A365-specific metadata like agent ID and tenant ID

**Clips:**

1. Finally, Agent 365 telemetry. The same spans appear here with enriched attributes, normalized naming, agent ID, and tenant ID. The A365 instrumentors bridge the agent framework, OpenAI, and LangChain traces into the A365 observability pipeline. All three backends, one function call.

---

## Closing

**Visual:** Back to the editor showing the `configure_microsoft_opentelemetry()` call → fade to title slide — "One Package. One Onboarding. Every Backend."

**Clips:**

1. One distro. Azure Monitor with traces, metrics, logs, and live metrics. OTLP with Jaeger and Prometheus. Console output for debugging. And A365 telemetry with enriched spans. All from a single function call. Less confusion for developers, less duplication across teams.

---

## Timing Estimates

| Scene | Clips | Approx. Duration |
|-------|-------|-------------------|
| 1 — The Current Issue | 2 | ~20 sec |
| 2 — The Proposed Solution | 2 | ~20 sec |
| 3 — Playground Calling the Agent | 1 | ~15 sec |
| 4 — Azure Monitor (traces, metrics, logs, live metrics) | 2 | ~20 sec |
| 5 — OTLP (Jaeger + Prometheus) | 1 | ~15 sec |
| 6 — Console Exporter | 1 | ~10 sec |
| 7 — A365 Telemetry | 1 | ~10 sec |
| Closing | 1 | ~10 sec |
| **Total** | **11** | **~2 min** |
