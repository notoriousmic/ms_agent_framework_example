"""Microsoft Agent Framework - Multi-agent AI orchestration."""

from microsoft_agent_framework.observability import setup_observability

from .config import settings

# Initialize observability/tracing for all agents
# Configuration is loaded from environment variables via settings
if settings.observability.enable_otel:
    setup_observability(
        enable_sensitive_data=settings.observability.enable_sensitive_data,
        otlp_endpoint=settings.observability.otlp_endpoint,
        applicationinsights_connection_string=settings.observability.applicationinsights_connection_string,
    )

__all__ = ["setup_observability", "settings"]
