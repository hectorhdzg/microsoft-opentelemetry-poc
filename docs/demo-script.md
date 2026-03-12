# Demo Script — Microsoft OpenTelemetry Distro

> **Format:** Each scene has narration text optimized for **Clipchamp text-to-speech**.
> Each numbered line is a **separate TTS clip**. Drop them onto the timeline and
> add silent gaps between clips to create pauses.
> Commas and periods within a clip provide natural micro-pauses.

---

## Scene 1 — The Problem: Too Many Products, Too Much Confusion

**Visual:** Title slide — "Observability for AI Agents Today" → show logos of Azure Monitor, A365, OTLP, OpenAI, LangChain scattered across the screen

**Clips:**

1. Today, if you're building an AI agent on Microsoft's platform, observability is fragmented. Azure Monitor has its own SDK and setup. Agent 365 has a completely separate observability stack. OpenAI, LangChain, among others come with different instrumentation packages and different onboarding guides.
2. As a developer, you have to discover, learn, and wire together pieces from multiple product teams, just to get traces flowing. And internally, each team is solving the same problems independently, duplicating effort across the organization.
3. The result is customer confusion, duplicated engineering work, and tons of boilerplate code before you write a single line of agent logic.

---

## Scene 2 — One Package, One Onboarding Experience

**Visual:** Split screen — `src/observability_config.py` on the left (scroll through), `src/microsoft_distro_observability_config.py` on the right

**Clips:**

1. The Microsoft OpenTelemetry Distro solves this by giving customers one package, one API, and one set of documentation, no matter which backends they need. Azure Monitor, A365, OTLP, GenAI instrumentations, all configured through a single function call.
2. On the left is the manual approach. You wire together multiple SDKs, initialize each instrumentor separately and dependency checks. On the right, the distro. One import. One call. Same telemetry output.
3. And internally, this means teams stop duplicating effort. Shared instrumentation setup, shared exporter wiring, shared bug fixes. One codebase that benefits every backend.

---

## Scene 3 — What the Distro Handles

**Visual:** Architecture diagram showing the distro's components

**Clips:**

1. Under the hood, the distro brings together exporters for Azure Monitor, OTLP, and A365.  GenAI community instrumentations. And standard web frameworks like Django, FastAPI, and Flask. All from one centralized package.
2. Customers get one install command and one function call. They can also drive everything from environment variables with zero code changes. No more hunting across docs from different teams.

---

## Scene 4 — Live Telemetry & Closing

**Visual:** Show `src/host_agent_server.py` import line change → then switch to Azure Monitor Application Insights dashboard → then A365 telemetry view → end with title slide "One Onboarding Experience. Less Confusion. No Duplication."

**Clips:**

1. Switching is as simple as changing one import in your host agent server. From observability config, to microsoft distro observability config. Same agent, same telemetry, no other changes.
2. Here's sample telemetry from this project running with the distro. In Azure Monitor, you can see traces, dependencies, and performance metrics flowing into Application Insights. And in Agent 365, the same agent spans appear with enriched attributes and normalized naming. Both backends, powered by one function call.
3. The Microsoft OpenTelemetry Distro gives customers one onboarding experience instead of many. It eliminates duplication across product teams. And it cuts boilerplate down to a single function call. One package. One API. Full observability.

---

## Timing Estimates

| Scene | Clips | Approx. Duration |
|-------|-------|-------------------|
| 1 — The Problem: Too Many Products | 3 | ~30 sec |
| 2 — One Package, One Onboarding | 3 | ~35 sec |
| 3 — What the Distro Handles | 2 | ~25 sec |
| 4 — Live Telemetry & Closing | 3 | ~30 sec |
| **Total** | **11** | **~2 min** |
