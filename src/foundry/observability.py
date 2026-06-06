"""OpenTelemetry wiring for Foundry tracing + monitoring.

When ``APPLICATIONINSIGHTS_CONNECTION_STRING`` is set, this module exports GenAI
spans (model calls, agent runs, and the replenishment workflow) to Application
Insights. The same App Insights resource is connected to the Foundry project
(see ``infra/bicep/main.bicep``), so the spans show up in the portal's
**Tracing** and **Monitoring** tabs for the project.

It is safe to call :func:`configure_observability` more than once and safe to
call when telemetry is disabled — in that case it is a no-op and the demo runs
fully offline.
"""

from __future__ import annotations

from functools import cache

from app.config import settings

_SERVICE_NAME = "warehouse-replenishment-foundry"


@cache
def configure_observability() -> bool:
    """Configure Azure Monitor + GenAI instrumentation. Returns True if enabled.

    Cached so repeated calls (per request, per script) are cheap and idempotent.
    """
    if not settings.tracing_enabled:
        return False

    try:
        import os

        from azure.monitor.opentelemetry import configure_azure_monitor
    except ImportError:
        # Telemetry deps not installed — degrade silently to no tracing.
        return False

    # Capture prompt/response content on GenAI spans so the Foundry portal shows
    # the actual narration alongside the deterministic facts.
    os.environ.setdefault(
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "true"
    )

    configure_azure_monitor(
        connection_string=settings.applicationinsights_connection_string,
        resource_attributes={"service.name": _SERVICE_NAME},
    )

    # Instrument the OpenAI client used by the raw chat-completion path.
    try:
        from opentelemetry.instrumentation.openai_v2 import OpenAIInstrumentor

        OpenAIInstrumentor().instrument()
    except Exception:  # pragma: no cover - optional instrumentation
        pass

    return True


def get_tracer():
    """Return an OpenTelemetry tracer for the demo's own workflow spans."""
    from opentelemetry import trace

    return trace.get_tracer(_SERVICE_NAME)
