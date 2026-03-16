# =============================================================================
# Temporary workarounds for pre-release dependency bugs.
# Import this module BEFORE any A365 or agent_framework code.
# Remove once the upstream packages ship fixes.
# =============================================================================

# ---------------------------------------------------------------------------
# 1. EnrichedReadableSpan missing private SDK attributes
#    Package: microsoft_agents_a365 (tested through 0.2.1.dev35)
#    Bug: A365's EnrichedReadableSpan wraps a ReadableSpan but only exposes
#         public properties. The OTLP exporter's encode_spans() accesses
#         private attributes (_context, _attributes, _events, _links, etc.)
#         directly, causing AttributeError and dropping all spans.
#    Fix: Add __getattr__ to proxy missing attribute lookups to the inner _span.
# ---------------------------------------------------------------------------
try:
    from microsoft_agents_a365.observability.core.exporters.enriched_span import (
        EnrichedReadableSpan,
    )

    def _enriched_getattr(self, name):
        return getattr(self._span, name)

    EnrichedReadableSpan.__getattr__ = _enriched_getattr
except ImportError:
    pass

# ---------------------------------------------------------------------------
# 2. agent_framework API renames (ChatAgent -> Agent, etc.)
#    Package: microsoft_agents_a365.tooling.extensions
#    Bug: The A365 tooling extensions package still references the old names
#         (ChatAgent, ChatMessage, ChatMessageStoreProtocol) that were renamed
#         in agent-framework >= 1.0.0rc1 to Agent, Message, and removed.
#    Fix: Patch the old aliases onto the agent_framework module so the import
#         in A365 tooling doesn't fail.
# ---------------------------------------------------------------------------
import agent_framework

if not hasattr(agent_framework, "ChatAgent"):
    agent_framework.ChatAgent = agent_framework.Agent
if not hasattr(agent_framework, "ChatMessage"):
    agent_framework.ChatMessage = agent_framework.Message
if not hasattr(agent_framework, "ChatMessageStoreProtocol"):
    agent_framework.ChatMessageStoreProtocol = type(
        "ChatMessageStoreProtocol", (), {}
    )
