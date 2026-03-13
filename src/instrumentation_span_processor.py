# Copyright (c) Microsoft. All rights reserved.

"""
Shared SpanProcessor that stamps every span with instrumentation metadata.

Used by both observability_config.py (A365 manual approach) and
microsoft_distro_observability_config.py (microsoft-opentelemetry distro).

Attributes added to each span on start:
  - observability.setup            : "a365-manual" or "microsoft-distro"
  - instrumentation.enabled        : comma-separated list of active instrumentors
  - instrumentation.*.version      : version of each instrumentation package
  - instrumentation.*.status       : "enabled" or "disabled" for each instrumentor
  - otel.sdk.version               : OpenTelemetry SDK version
  - agent_framework.version        : Agent Framework Core version
"""

from __future__ import annotations

import importlib.metadata as _md
from typing import Optional, Sequence

from opentelemetry.context import Context
from opentelemetry.sdk.trace import SpanProcessor, ReadableSpan
from opentelemetry.trace import Span


# Package-to-instrumentor mapping used to resolve versions and names
_INSTRUMENTORS = {
    "agentframework": "microsoft-agents-a365-observability-extensions-agent-framework",
    "openai": "microsoft-agents-a365-observability-extensions-openai",
    "langchain": "microsoft-agents-a365-observability-extensions-langchain",
}

_INFRA_PACKAGES = {
    "otel.sdk": "opentelemetry-sdk",
    "agent_framework.core": "agent-framework-core",
    "a365.observability.core": "microsoft-agents-a365-observability-core",
}


def _pkg_version(pip_name: str) -> str:
    try:
        return _md.version(pip_name)
    except _md.PackageNotFoundError:
        return "not-installed"


class InstrumentationSpanProcessor(SpanProcessor):
    """Adds instrumentation metadata attributes to every span on_start."""

    def __init__(
        self,
        *,
        setup_approach: str,
        enabled_instrumentors: Sequence[str] = (),
    ) -> None:
        """
        Args:
            setup_approach: identifier for the observability approach,
                e.g. "a365-manual" or "microsoft-distro".
            enabled_instrumentors: keys from _INSTRUMENTORS that were
                successfully enabled (e.g. ["agentframework", "openai"]).
        """
        self._attrs: dict[str, str] = {}

        # Approach
        self._attrs["observability.setup"] = setup_approach

        # Enabled list
        self._attrs["instrumentation.enabled"] = ",".join(enabled_instrumentors) or "none"

        # Per-instrumentor status + version
        for key, pip_name in _INSTRUMENTORS.items():
            status = "enabled" if key in enabled_instrumentors else "disabled"
            self._attrs[f"instrumentation.{key}.status"] = status
            self._attrs[f"instrumentation.{key}.version"] = _pkg_version(pip_name)

        # Infrastructure versions
        for attr_key, pip_name in _INFRA_PACKAGES.items():
            self._attrs[attr_key + ".version"] = _pkg_version(pip_name)

        # Distro version (only meaningful for microsoft-distro approach)
        if setup_approach == "microsoft-distro":
            self._attrs["microsoft_opentelemetry.version"] = _pkg_version("microsoft-opentelemetry")

    def on_start(self, span: Span, parent_context: Optional[Context] = None) -> None:
        for k, v in self._attrs.items():
            span.set_attribute(k, v)

    def on_end(self, span: ReadableSpan) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
