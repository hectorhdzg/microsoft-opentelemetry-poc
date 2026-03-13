# Demo Script — Microsoft OpenTelemetry Distro

> **Format:** Each scene has narration text optimized for **Clipchamp text-to-speech**.
> Each numbered line is a **separate TTS clip**. Drop them onto the timeline and
> add silent gaps between clips to create pauses.
> Commas and periods within a clip provide natural micro-pauses.

---

## Scene 1 — The Problem

**Visual:** Title slide — "Observability for AI Agents Today" → transition to logos of Azure Monitor, A365, OTLP, OpenAI, LangChain appearing separately across the screen

**Clips:**

1. Today, observability for AI agents on Microsoft's platform is fragmented. Azure Monitor has its own SDK. Agent 365 has a completely separate observability stack. OpenAI and LangChain each come with different instrumentation packages and different onboarding paths.
2. Developers have to discover and wire together pieces from multiple product teams just to get traces flowing. And internally, each team is solving the same problems independently, duplicating effort across the organization.

---

## Scene 2 — What This Looks Like in Code

**Visual:** Open `src/observability_config.py` in the editor, scroll through it slowly — highlight the tracer provider setup, then each instrumentor block, then the token cache and logger config

**Clips:**

1. Let's look at what that means in practice. This is observability config dot py from a real Agent Framework agent. It's about 250 lines. First you configure loggers. Then you call the A365 SDK's configure function to create a tracer provider and attach an exporter.
2. Then you initialize each instrumentor separately. Agent Framework. OpenAI Agents. LangChain. Each one is a separate import, separate error handling, separate config. And if you also want Azure Monitor, that's another SDK with its own setup on top.

---

## Scene 3 — The Distro Approach

**Visual:** Open `src/microsoft_distro_observability_config.py` in the editor — show the full file, then zoom into the `configure_microsoft_opentelemetry()` call and its parameters

**Clips:**

1. The Microsoft OpenTelemetry Distro replaces all of that with one package and one function call. This is the same agent, about 60 lines. You pass in which exporters you want and which instrumentations to enable.
2. Azure Monitor, A365, OTLP, Agent Framework, OpenAI, LangChain. All on the same function. One set of docs. One onboarding experience instead of four.

---

## Scene 4 — Switching and Live Telemetry

**Visual:** Open `src/host_agent_server.py` — highlight the import line change → then switch to browser showing Application Insights traces → then A365 telemetry view with enriched spans

**Clips:**

1. To switch, you change one import in host agent server dot py. From observability config to microsoft distro observability config. Same agent, no other changes.
2. Here's the telemetry. In Application Insights, you can see the agent's traces, dependencies, and requests. OpenAI calls show up with model and token details. And in Agent 365, the same spans appear with enriched attributes and normalized naming. Both backends, one function call.

---

## Scene 5 — Closing

**Visual:** Back to the editor showing the `configure_microsoft_opentelemetry()` call, then fade to title slide — "One Package. One Onboarding. Less Duplication."

**Clips:**

1. One package replaces the fragmented setup across Azure Monitor, A365, and GenAI libraries. Less confusion for developers, less duplication across teams, and a lot less code to maintain.

---

## Timing Estimates

| Scene | Clips | Approx. Duration |
|-------|-------|-------------------|
| 1 — The Problem | 2 | ~20 sec |
| 2 — What This Looks Like in Code | 2 | ~25 sec |
| 3 — The Distro Approach | 2 | ~20 sec |
| 4 — Switching and Live Telemetry | 2 | ~25 sec |
| 5 — Closing | 1 | ~10 sec |
| **Total** | **9** | **~2 min** |
