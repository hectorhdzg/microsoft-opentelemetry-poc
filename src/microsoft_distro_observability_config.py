# Copyright (c) Microsoft. All rights reserved.

"""
Observability Configuration using Microsoft OpenTelemetry Distro.

This replaces the A365 manual approach (observability_config.py) with a single
call to configure_microsoft_opentelemetry() from the microsoft-opentelemetry
package. Compare the two files to see the difference in code required.

  A365 approach (observability_config.py):
    - ~250 lines
    - Manual TracerProvider setup via A365 configure()
    - 4 separate instrumentor initializations (AgentFramework, OpenAI, SK, LangChain)
    - Token cache management
    - Logger configuration
    - 6 pip packages for observability extensions

  Microsoft Distro approach (this file):
    - ~60 lines
    - One function call: configure_microsoft_opentelemetry()
    - All exporters + instrumentations enabled via parameters or env vars
    - Token cache still needed for A365 exporter auth

Environment Variables:
  ┌────────────────────────────────────────────────────┬──────────────────────────────────────────────┐
  │ Variable                                           │ Purpose                                      │
  ├────────────────────────────────────────────────────┼──────────────────────────────────────────────┤
  │ ENABLE_INSTRUMENTATION=true                        │ Turns on span creation in AgentFramework SDK │
  │ ENABLE_SENSITIVE_DATA=true                         │ Include message content in spans              │
  │ APPLICATIONINSIGHTS_CONNECTION_STRING               │ Azure Monitor / App Insights (optional)      │
  │ ENABLE_OTLP_EXPORTER=true                          │ Send spans via OTLP (optional)               │
  │ OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318  │ OTLP collector endpoint                      │
  │ ENABLE_A365_EXPORTER=true                          │ Send spans to A365 cloud backend             │
  └────────────────────────────────────────────────────┴──────────────────────────────────────────────┘

Installation:
  pip install microsoft-opentelemetry
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

from token_cache import cache_agentic_token, get_cached_agentic_token  # noqa: F401

# =============================================================================
# PUBLIC API — call once at startup
# =============================================================================

def setup_observability() -> bool:
    """
    One-call entry point to configure all observability.

    Replaces:
      - A365 configure() call
      - AgentFrameworkInstrumentor().instrument()
      - OpenAIAgentsTraceInstrumentor().instrument()
      - CustomLangChainInstrumentor()
      - Logger configuration

    With a single call to configure_microsoft_opentelemetry().
    """
    try:
        from microsoft.opentelemetry import configure_microsoft_opentelemetry
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.trace import get_tracer_provider
        from instrumentation_span_processor import InstrumentationSpanProcessor

        # All A365 instrumentors we're requesting
        enabled = ["agentframework", "openai", "langchain"]
        meta_processor = InstrumentationSpanProcessor(
            setup_approach="microsoft-distro",
            enabled_instrumentors=enabled,
        )

        enable_otlp = os.getenv("ENABLE_OTLP_EXPORTER", "false").lower() == "true"
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

        # Build the OTLP metric reader so it's included in the MeterProvider
        # at creation time. MeterProvider doesn't support adding readers after
        # init, so we must pass it via metric_readers=[...].
        otlp_metric_readers = []
        if enable_otlp and otlp_endpoint:
            from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
            from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter

            otlp_metric_readers.append(
                PeriodicExportingMetricReader(
                    OTLPMetricExporter(endpoint=f"{otlp_endpoint}/v1/metrics"),
                    export_interval_millis=10000,
                )
            )
            logger.info("OTLP metric reader prepared (endpoint=%s)", otlp_endpoint)

        configure_microsoft_opentelemetry(
            # --- Exporters ---
            # Azure Monitor (enabled automatically if APPLICATIONINSIGHTS_CONNECTION_STRING is set)
            # enable_azure_monitor_export=True,

            # OTLP — let the distro handle log/metric OTLP exporters
            # (we add the trace exporter manually below for reliability)
            enable_otlp_export=enable_otlp,

            # A365 cloud exporter
            enable_a365_export=os.getenv("ENABLE_A365_EXPORTER", "false").lower() == "true",
            a365_token_resolver=lambda agent_id, tenant_id: get_cached_agentic_token(tenant_id, agent_id),

            # Metadata processor only — we add the OTLP/Console processors
            # directly to the SDK TracerProvider after setup.
            span_processors=[meta_processor],

            # OTLP metric reader — must be passed at init time
            metric_readers=otlp_metric_readers,

            # --- A365 framework instrumentations (all enabled) ---
            enable_a365_agentframework_instrumentation=True,
            enable_a365_openai_instrumentation=True,
            enable_a365_langchain_instrumentation=True,

            # --- GenAI OTel contrib instrumentations (optional) ---
            # enable_genai_openai_instrumentation=True,
            # enable_genai_openai_agents_instrumentation=True,
            # enable_genai_langchain_instrumentation=True,
        )

        # After configure_microsoft_opentelemetry, the global TracerProvider is
        # set by Azure Monitor. Add the OTLP exporter directly to the SDK
        # TracerProvider so spans flow to the collector.  The distro's own
        # _add_otlp_exporters also adds one, but adding ours directly to the
        # resolved provider guarantees it's on the real SDK TracerProvider.
        tp = get_tracer_provider()
        real_tp = getattr(tp, "_real_tracer_provider", tp)
        if not isinstance(real_tp, TracerProvider):
            real_tp = tp
        if isinstance(real_tp, TracerProvider):
            if enable_otlp and otlp_endpoint:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                    OTLPSpanExporter as HttpOTLPSpanExporter,
                )
                real_tp.add_span_processor(
                    BatchSpanProcessor(HttpOTLPSpanExporter(endpoint=otlp_endpoint))
                )
                logger.info("OTLP span processor added to TracerProvider (endpoint=%s)", otlp_endpoint)
        else:
            logger.warning("TracerProvider is %s, cannot add OTLP exporter directly", type(real_tp))

        logger.info("Observability configured via microsoft-opentelemetry distro")
        return True

    except Exception as e:
        logger.error("Failed to configure observability: %s", e)
        return False
