# Copyright (c) Microsoft. All rights reserved.

"""
Observability Configuration using Microsoft OpenTelemetry Distro.

This replaces the A365 manual approach (observability_config.py) with a single
call to configure_microsoft_opentelemetry(). Compare the two files to see the
difference in code required.

  A365 manual approach (observability_config.py):
    - ~170 lines
    - Manual TracerProvider setup via A365 configure()
    - 3 separate instrumentor initializations (AgentFramework, OpenAI, LangChain)
    - Token cache management
    - Logger configuration

  Microsoft Distro approach (this file):
    - ~50 lines
    - One function call: configure_microsoft_opentelemetry()
    - All exporters + instrumentations enabled via parameters or env vars
    - Token cache still needed for A365 exporter auth

Environment Variables:
  APPLICATIONINSIGHTS_CONNECTION_STRING  — Azure Monitor (auto-enables when set)
  ENABLE_OTLP_EXPORTER=true             — OTLP export (Jaeger, Prometheus)
  OTEL_EXPORTER_OTLP_ENDPOINT           — OTLP collector endpoint
  ENABLE_A365_EXPORTER=true              — A365 cloud backend
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

from token_cache import get_cached_agentic_token


def setup_observability() -> bool:
    """One-call entry point to configure all observability via the distro."""
    try:
        from microsoft.opentelemetry import configure_microsoft_opentelemetry
        from instrumentation_span_processor import configure_log_levels

        configure_log_levels()

        configure_microsoft_opentelemetry(
            # --- Exporters (Azure Monitor auto-enabled via env var) ---
            enable_otlp_export=os.getenv("ENABLE_OTLP_EXPORTER", "false").lower() == "true",
            enable_a365_export=os.getenv("ENABLE_A365_EXPORTER", "false").lower() == "true",
            a365_token_resolver=lambda agent_id, tenant_id: get_cached_agentic_token(tenant_id, agent_id),
            # --- A365 instrumentations ---
            enable_a365_agentframework_instrumentation=True,
            enable_a365_openai_instrumentation=True,
            enable_a365_langchain_instrumentation=True,
        )

        logger.info("Observability configured via microsoft-opentelemetry distro")
        return True

    except Exception as e:
        logger.error("Failed to configure observability: %s", e)
        return False
