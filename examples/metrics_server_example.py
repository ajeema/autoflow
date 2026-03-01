"""
Example HTTP server for exposing metrics to Alloy/Grafana.

This demonstrates how to serve Prometheus metrics that Alloy can scrape.
"""

from aiohttp import web
import time

from autoflow.context_graph.observability import global_registry, format_prometheus_metrics
from autoflow.context_graph.audit import Auditor, FileAuditBackend


async def metrics_handler(request: web.Request) -> web.Response:
    """Serve Prometheus metrics for scraping."""
    metrics_text = format_prometheus_metrics(global_registry)
    return web.Response(
        text=metrics_text,
        content_type="text/plain; version=0.0.4; charset=utf-8",
    )


async def health_handler(request: web.Request) -> web.Response:
    """Health check endpoint."""
    return web.json_response({"status": "healthy"})


def create_app() -> web.Application:
    """Create the aiohttp application."""
    app = web.Application()
    app.router.add_get("/metrics", metrics_handler)
    app.router.add_get("/health", health_handler)
    return app


if __name__ == "__main__":
    # Add some sample metrics
    global_registry.counter("api_requests_total", tags={"endpoint": "/api/entities"})
    global_registry.gauge("active_connections", 42)
    global_registry.histogram("request_duration_ms", 45.2)

    # Start server
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=9090)
    print("Metrics server running on http://localhost:9090/metrics")
