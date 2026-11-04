
"""
AEGIS Configuration

Central location for application settings.
"""

import os

APP_NAME = "AEGIS"
APP_VERSION = "0.1.0"

DEBUG_MODE = os.getenv(
    "AEGIS_DEBUG",
    "true"
).strip().lower() in {"1", "true", "yes", "on"}

AGENT_DESCRIPTION = (
    "A self-learning AI agent that improves "
    "through experience and user feedback."
)
