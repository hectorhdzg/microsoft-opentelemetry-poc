# Copyright (c) Microsoft. All rights reserved.

"""
Observability Configuration — Single source of truth for all telemetry setup.

This module centralizes:
  1. Environment variables required for observability
  2. Logging configuration for observability-related loggers
  3. A365 Observability SDK configure() call (TracerProvider + exporter)
  4. AgentFramework auto-instrumentation (span processor + enricher)
  5. Token cache for A365 exporter authentication

Environment Variables:
  ┌──────────────────────────────────────────┬────────────────────────────────────────────────┐
  │ Variable                                 │ Purpose                                        │
  ├──────────────────────────────────────────┼────────────────────────────────────────────────┤
  │ ENABLE_INSTRUMENTATION=true              │ Turns on span creation in AgentFramework SDK   │
  │ ENABLE_SENSITIVE_DATA=true               │ Include message content in spans                │
  │ ENABLE_OBSERVABILITY=true                │ Master switch for observability                 │
  │ ENABLE_A365_OBSERVABILITY_EXPORTER=false │ false → ConsoleSpanExporter (dev)               │
  │                                          │ true  → A365 cloud exporter (requires auth)     │
  │ OBSERVABILITY_SERVICE_NAME               │ Service name tag on all spans                   │
  │ OBSERVABILITY_SERVICE_NAMESPACE           │ Service namespace tag on all spans              │
  │ ENABLE_OTEL=true                         │ Enable OTEL logs in AgentFramework SDK          │
  ├──────────────────────────────────────────┼────────────────────────────────────────────────┤
  │ ** Required only when A365 exporter is enabled **                                         │
  │ AUTH_HANDLER_NAME=AGENTIC                │ Enables agentic auth flow for token exchange    │
  │ CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID     │ AAD app client ID               │
  │ CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET │ AAD app client secret            │
  │ CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID     │ AAD tenant ID                   │
  │ CONNECTIONS__SERVICE_CONNECTION__SETTINGS__SCOPES       │ Required API scopes             │
  │ CONNECTIONSMAP_0_SERVICEURL=*            │ Service URL mapping                             │
  │ CONNECTIONSMAP_0_CONNECTION=SERVICE_CONNECTION │ Connection name mapping                   │
  └──────────────────────────────────────────┴────────────────────────────────────────────────┘
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

from token_cache import cache_agentic_token, get_cached_agentic_token  # noqa: F401

# =============================================================================
# 1. LOGGING CONFIGURATION
# =============================================================================

def _configure_loggers() -> None:
    """Set log levels for observability and agents SDK loggers."""
    logging.getLogger("microsoft_agents_a365.observability").setLevel(logging.INFO)

    ms_agents_logger = logging.getLogger("microsoft_agents")
    ms_agents_logger.addHandler(logging.StreamHandler())
    ms_agents_logger.setLevel(logging.INFO)


# =============================================================================
# 3. A365 OBSERVABILITY SDK — configure()
# =============================================================================

def _configure_a365_observability() -> bool:
    """
    Call the A365 observability SDK ``configure()`` to set up the TracerProvider
    and attach the appropriate exporter.

    When ENABLE_A365_OBSERVABILITY_EXPORTER=true **and** a token_resolver is
    available, spans are sent to the A365 cloud backend.
    Otherwise, spans are printed to the console via ConsoleSpanExporter.
    """
    from microsoft_agents_a365.observability.core.config import configure

    service_name = os.getenv("OBSERVABILITY_SERVICE_NAME", "agent-framework-sample")
    service_namespace = os.getenv("OBSERVABILITY_SERVICE_NAMESPACE", "agent-framework.samples")

    return configure(
        service_name=service_name,
        service_namespace=service_namespace,
        token_resolver=lambda agent_id, tenant_id: get_cached_agentic_token(tenant_id, agent_id),
    )


# =============================================================================
# 4. AGENTFRAMEWORK AUTO-INSTRUMENTATION
# =============================================================================

def _instrument_agentframework() -> bool:
    """
    Attach the AgentFramework span processor and enricher so that every
    ChatAgent.invoke() call produces OpenTelemetry spans automatically.

    Returns True if instrumentation succeeded.
    """
    try:
        from microsoft_agents_a365.observability.extensions.agentframework.trace_instrumentor import (
            AgentFrameworkInstrumentor,
        )

        AgentFrameworkInstrumentor().instrument(skip_dep_check=True)
        logger.info("AgentFramework auto-instrumentation enabled")
        return True
    except Exception as e:
        logger.warning("Failed to enable AgentFramework instrumentation: %s", e)
        return False


# =============================================================================
# 5. OPENAI AGENTS SDK INSTRUMENTATION
# =============================================================================

def _instrument_openai_agents() -> bool:
    """
    Attach the OpenAI Agents SDK trace processor so that spans from the
    OpenAI Agents SDK are forwarded into the A365 tracing pipeline.

    Package: microsoft-agents-a365-observability-extensions-openai
    """
    try:
        from microsoft_agents_a365.observability.extensions.openai.trace_instrumentor import (
            OpenAIAgentsTraceInstrumentor,
        )

        OpenAIAgentsTraceInstrumentor().instrument(skip_dep_check=True)
        logger.info("OpenAI Agents SDK auto-instrumentation enabled")
        return True
    except Exception as e:
        logger.warning("Failed to enable OpenAI Agents SDK instrumentation: %s", e)
        return False


# =============================================================================
# 6. SEMANTIC KERNEL INSTRUMENTATION
# =============================================================================

def _instrument_semantic_kernel() -> bool:
    """
    Attach the Semantic Kernel span processor so that SK function invocations
    and kernel operations produce spans in the A365 pipeline.

    Package: microsoft-agents-a365-observability-extensions-semantic-kernel
    """
    try:
        from microsoft_agents_a365.observability.extensions.semantickernel.trace_instrumentor import (
            SemanticKernelInstrumentor,
        )

        SemanticKernelInstrumentor().instrument(skip_dep_check=True)
        logger.info("Semantic Kernel auto-instrumentation enabled")
        return True
    except Exception as e:
        logger.warning("Failed to enable Semantic Kernel instrumentation: %s", e)
        return False


# =============================================================================
# 7. LANGCHAIN INSTRUMENTATION
# =============================================================================

def _instrument_langchain() -> bool:
    """
    Attach the LangChain tracer so that every LangChain run (chains, agents,
    LLM calls, tool calls) produces spans in the A365 pipeline.

    Note: CustomLangChainInstrumentor calls instrument() inside __init__,
    so we just need to instantiate it.

    Package: microsoft-agents-a365-observability-extensions-langchain
    """
    try:
        from microsoft_agents_a365.observability.extensions.langchain.tracer_instrumentor import (
            CustomLangChainInstrumentor,
        )

        CustomLangChainInstrumentor()  # instrument() is called in __init__
        logger.info("LangChain auto-instrumentation enabled")
        return True
    except Exception as e:
        logger.warning("Failed to enable LangChain instrumentation: %s", e)
        return False


# =============================================================================
# 8. PUBLIC API — call once at startup
# =============================================================================

def setup_observability() -> bool:
    """
    One-call entry point to configure all observability.

    Call this **once** during application startup, before the agent is created.
    It will:
      1. Configure loggers
      2. Set up the TracerProvider + exporter (console or A365)
      3. Attach AgentFramework auto-instrumentation
      4. Attach OpenAI Agents SDK instrumentation
      5. Attach Semantic Kernel instrumentation
      6. Attach LangChain instrumentation

    Returns True if configure and at least AgentFramework instrumentation succeeded.
    """
    _configure_loggers()

    configured = _configure_a365_observability()
    if not configured:
        logger.error("A365 observability configure() failed")
        return False
    logger.info("A365 observability configured (TracerProvider + exporter ready)")

    # Instrument all supported frameworks
    results = {
        "AgentFramework": _instrument_agentframework(),
        "OpenAI Agents":  _instrument_openai_agents(),
        "Semantic Kernel": _instrument_semantic_kernel(),
        "LangChain":       _instrument_langchain(),
    }

    # Map display names → processor keys
    _key_map = {
        "AgentFramework": "agentframework",
        "OpenAI Agents": "openai",
        "Semantic Kernel": "semantic_kernel",
        "LangChain": "langchain",
    }
    enabled = [_key_map[name] for name, ok in results.items() if ok]

    # Attach shared InstrumentationSpanProcessor
    from instrumentation_span_processor import InstrumentationSpanProcessor
    from opentelemetry.trace import get_tracer_provider

    proc = InstrumentationSpanProcessor(setup_approach="a365-manual", enabled_instrumentors=enabled)
    tp = get_tracer_provider()
    if hasattr(tp, "add_span_processor"):
        tp.add_span_processor(proc)
        logger.info("InstrumentationSpanProcessor attached")

    exporter = "A365" if os.getenv("ENABLE_A365_OBSERVABILITY_EXPORTER", "false").lower() == "true" else "Console"
    status = ", ".join(f"{name}: {'on' if ok else 'off'}" for name, ok in results.items())
    logger.info("Observability setup complete — exporter: %s | %s", exporter, status)

    return configured and results["AgentFramework"]
