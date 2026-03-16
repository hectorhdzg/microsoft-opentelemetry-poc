# Copyright (c) Microsoft. All rights reserved.

"""
Observability Configuration — A365 manual approach.

This is the "current way" of adding observability to an Agent Framework app
using the A365 SDK directly. Compare with microsoft_distro_observability_config.py
which does the same thing in a single function call via the microsoft-opentelemetry distro.

Steps:
  1. Suppress noisy SDK loggers
  2. Call A365 configure() to set up TracerProvider + A365/console exporter
  3. Wire up Azure Monitor (traces, metrics, logs)
  4. Wire up OTLP export (traces, metrics, logs) for Jaeger/Prometheus
  5. Instrument AgentFramework, OpenAI Agents SDK, LangChain — one by one
  6. Attach metadata span processor

Environment Variables:
  ENABLE_INSTRUMENTATION=true                        — Turns on span creation in AgentFramework SDK
  ENABLE_SENSITIVE_DATA=true                         — Include message content in spans
  APPLICATIONINSIGHTS_CONNECTION_STRING              — Azure Monitor / App Insights
  ENABLE_OTLP_EXPORTER=true                         — Send telemetry via OTLP
  OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318  — OTLP collector endpoint
  ENABLE_A365_EXPORTER=true                          — A365 cloud backend
  OBSERVABILITY_SERVICE_NAME                         — Service name tag on all spans
  OBSERVABILITY_SERVICE_NAMESPACE                    — Service namespace tag on all spans
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

from token_cache import cache_agentic_token, get_cached_agentic_token  # noqa: F401


def setup_observability() -> bool:
    """
    One-call entry point — configure all observability the "manual" way.

    Call once during application startup, before the agent is created.
    """

    # ── 1. Suppress noisy loggers ────────────────────────────────────────
    for name in (
        "azure.core.pipeline.policies.http_logging_policy",
        "azure.monitor.opentelemetry",
        "azure.monitor.opentelemetry.exporter",
        "azure.identity",
        "opentelemetry.exporter.otlp",
        "opentelemetry.exporter.otlp.proto.http._log_exporter",
        "urllib3.connectionpool",
    ):
        logging.getLogger(name).setLevel(logging.WARNING)
    logging.getLogger("opentelemetry.exporter.otlp.proto.http._log_exporter").setLevel(logging.CRITICAL)
    logging.getLogger("microsoft_agents_a365.observability").setLevel(logging.INFO)
    ms_agents_logger = logging.getLogger("microsoft_agents")
    ms_agents_logger.addHandler(logging.StreamHandler())
    ms_agents_logger.setLevel(logging.INFO)

    # ── 2. A365 TracerProvider + exporter ────────────────────────────────
    from microsoft_agents_a365.observability.core.config import configure

    configured = configure(
        service_name=os.getenv("OBSERVABILITY_SERVICE_NAME", "agent-framework-sample"),
        service_namespace=os.getenv("OBSERVABILITY_SERVICE_NAMESPACE", "agent-framework.samples"),
        token_resolver=lambda agent_id, tenant_id: get_cached_agentic_token(tenant_id, agent_id),
    )
    if not configured:
        logger.error("A365 observability configure() failed")
        return False

    # ── 3. Azure Monitor ─────────────────────────────────────────────────
    #    Manually set up Azure Monitor trace, metric, and log exporters.
    #    The distro does this with one flag; here we need to wire each one.
    from opentelemetry.trace import get_tracer_provider
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    tp = get_tracer_provider()
    real_tp = getattr(tp, "_real_tracer_provider", tp)
    if not isinstance(real_tp, TracerProvider):
        real_tp = tp

    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if connection_string:
        from azure.monitor.opentelemetry.exporter import (
            AzureMonitorTraceExporter,
            AzureMonitorMetricExporter,
            AzureMonitorLogExporter,
        )
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.metrics import set_meter_provider
        from opentelemetry.sdk._logs import LoggerProvider
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
        from opentelemetry._logs import set_logger_provider

        # Traces → App Insights
        if isinstance(real_tp, TracerProvider):
            real_tp.add_span_processor(
                BatchSpanProcessor(AzureMonitorTraceExporter(connection_string=connection_string))
            )

        # Metrics → App Insights
        az_metric_reader = PeriodicExportingMetricReader(
            AzureMonitorMetricExporter(connection_string=connection_string),
            export_interval_millis=60000,
        )
        meter_provider = MeterProvider(metric_readers=[az_metric_reader])
        set_meter_provider(meter_provider)

        # Logs → App Insights
        az_log_provider = LoggerProvider()
        az_log_provider.add_log_record_processor(
            BatchLogRecordProcessor(AzureMonitorLogExporter(connection_string=connection_string))
        )
        set_logger_provider(az_log_provider)

        logger.info("Azure Monitor exporters added (traces + metrics + logs)")

    # ── 4. OTLP export (Jaeger / Prometheus / Collector) ─────────────────
    #    Again, the distro handles this with enable_otlp_export=True.
    #    Manually we need to create each exporter and attach it.
    enable_otlp = os.getenv("ENABLE_OTLP_EXPORTER", "false").lower() == "true"
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    if enable_otlp and otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.metrics import get_meter_provider, set_meter_provider
        from opentelemetry.sdk._logs import LoggerProvider
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
        from opentelemetry._logs import get_logger_provider, set_logger_provider

        # Traces → OTLP
        if isinstance(real_tp, TracerProvider):
            real_tp.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces"))
            )

        # Metrics → OTLP
        otlp_metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=f"{otlp_endpoint}/v1/metrics"),
            export_interval_millis=10000,
        )
        existing_mp = get_meter_provider()
        if not isinstance(existing_mp, MeterProvider):
            # No SDK MeterProvider yet — create one with the OTLP reader
            set_meter_provider(MeterProvider(metric_readers=[otlp_metric_reader]))
        # If Azure Monitor already created one, we can't add readers after init —
        # we'd need to recreate the MeterProvider with both readers.
        # This is one of the pain points the distro solves.

        # Logs → OTLP
        existing_lp = get_logger_provider()
        if isinstance(existing_lp, LoggerProvider):
            existing_lp.add_log_record_processor(
                BatchLogRecordProcessor(OTLPLogExporter(endpoint=f"{otlp_endpoint}/v1/logs"))
            )
        else:
            otlp_log_provider = LoggerProvider()
            otlp_log_provider.add_log_record_processor(
                BatchLogRecordProcessor(OTLPLogExporter(endpoint=f"{otlp_endpoint}/v1/logs"))
            )
            set_logger_provider(otlp_log_provider)

        logger.info("OTLP exporters added (traces + metrics + logs → %s)", otlp_endpoint)

    # ── 5. Instrument frameworks ─────────────────────────────────────────
    #    Each framework needs its own instrumentor import and .instrument() call.
    #    The distro enables all of these with boolean flags.
    from microsoft_agents_a365.observability.extensions.agentframework.trace_instrumentor import (
        AgentFrameworkInstrumentor,
    )
    from microsoft_agents_a365.observability.extensions.openai.trace_instrumentor import (
        OpenAIAgentsTraceInstrumentor,
    )
    from microsoft_agents_a365.observability.extensions.langchain.tracer_instrumentor import (
        CustomLangChainInstrumentor,
    )

    AgentFrameworkInstrumentor().instrument(skip_dep_check=True)
    OpenAIAgentsTraceInstrumentor().instrument(skip_dep_check=True)
    CustomLangChainInstrumentor()  # instrument() is called in __init__

    # ── 6. Metadata span processor ──────────────────────────────────────
    from instrumentation_span_processor import InstrumentationSpanProcessor

    if isinstance(real_tp, TracerProvider):
        real_tp.add_span_processor(
            InstrumentationSpanProcessor(
                setup_approach="a365-manual",
                enabled_instrumentors=["agentframework", "openai", "langchain"],
            )
        )

    logger.info("Observability configured (A365 manual approach)")
    return True
