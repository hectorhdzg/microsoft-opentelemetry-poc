# Copyright (c) Microsoft. All rights reserved.

# !/usr/bin/env python3
"""
Example: Direct usage of Generic Agent Host with AgentFrameworkAgent
This script demonstrates direct usage without complex imports.
"""

import sys

# ---------------------------------------------------------------------------
# Compatibility shim for agent_framework API renames
# The A365 tooling extensions package (microsoft_agents_a365.tooling.extensions)
# references names that were renamed in agent-framework >= 1.0.0rc1:
#   ChatAgent -> Agent,  ChatMessage -> Message,  ChatMessageStoreProtocol removed
# Patch the aliases before any A365 code is imported.
# ---------------------------------------------------------------------------
import agent_framework

if not hasattr(agent_framework, "ChatAgent"):
    agent_framework.ChatAgent = agent_framework.Agent
if not hasattr(agent_framework, "ChatMessage"):
    agent_framework.ChatMessage = agent_framework.Message
if not hasattr(agent_framework, "ChatMessageStoreProtocol"):
    # Provide a no-op placeholder so the import doesn't fail
    agent_framework.ChatMessageStoreProtocol = type(
        "ChatMessageStoreProtocol", (), {}
    )

try:
    from agent import AgentFrameworkAgent
    from host_agent_server import create_and_run_host
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure you're running from the correct directory")
    sys.exit(1)


def main():
    """Main entry point - start the generic host with AgentFrameworkAgent"""
    try:
        print("Starting Generic Agent Host with AgentFrameworkAgent...")
        print()

        # Use the convenience function to start hosting
        create_and_run_host(AgentFrameworkAgent)

    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
