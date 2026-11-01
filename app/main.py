"""
AEGIS - Self-Learning AI Agent

Main application entry point.
"""

from app.core.config import APP_VERSION, DEBUG_MODE
from app.agent.identity import (
    AGENT_NAME,
    AGENT_ROLE,
    AGENT_CAPABILITIES,
)


def main():
    print("=" * 50)
    print(f"{AGENT_NAME} - SELF-LEARNING AI AGENT")
    print("=" * 50)

    print(f"Version: {APP_VERSION}")
    print(f"Debug Mode: {DEBUG_MODE}")

    print("\nAgent Role:")
    print(AGENT_ROLE)

    print("\nAgent Capabilities:")

    for capability in AGENT_CAPABILITIES:
        print(f"- {capability}")

    print("\nAgent Status: Ready for Development")
    print("=" * 50)


if __name__ == "__main__":
    main()