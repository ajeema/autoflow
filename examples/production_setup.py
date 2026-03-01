"""
Production-ready HTTP server with metrics endpoint for Prometheus/Alloy scraping.

This example shows how to:
1. Set up an HTTP server with /metrics endpoint
2. Integrate with Context Graph Framework
3. Support multiple exporters
4. Configure for different environments

Usage:
    python production_setup.py

Then configure Alloy/Prometheus to scrape:
    http://localhost:9090/metrics
"""

from aiohttp import web
import os
from typing import Optional

from autoflow.context_graph.core import ContextGraph, Entity
from autoflow.context_graph.backends import InMemoryBackend
from autoflow.context_graph.observability import (
    MetricsRegistry,
    PerformanceTracker,
    global_registry,
)
from autoflow.context_graph.observability_exporters import (
    CompositeExporter,
    PrometheusFileExporter,
    PrometheusHTTPExporter,
    OTLPExporter,
    ConsoleExporter,
)
from autoflow.context_graph.observability_config import (
    ObservabilityConfig,
    create_exporter_from_config,
)


# ============================================================================
# Application Setup
# ============================================================================

class Application:
    """
    Application with observability integrated.

    Demonstrates production-ready setup with multiple exporters.
    """

    def __init__(self):
        """Initialize application with observability."""
        # Setup observability based on environment
        self.registry = self._setup_observability()

        # Setup performance tracker
        self.tracker = PerformanceTracker()

        # Setup context graph
        self.graph = ContextGraph(backend=InMemoryBackend())

        # Add some sample data
        self._add_sample_data()

    def _setup_observability(self) -> MetricsRegistry:
        """
        Setup observability based on environment.

        Returns:
            Configured metrics registry
        """
        env = os.getenv("ENVIRONMENT", "development")

        if env == "production":
            # Production: Export to Alloy + Prometheus file
            config = ObservabilityConfig.production_alloy(
                alloy_endpoint=os.getenv("OTLP_ENDPOINT", "http://alloy:4318"),
                metrics_file="/var/lib/node_exporter/textfile_collector/context_graph.prom",
            )
        elif env == "testing":
            # Testing: Minimal overhead
            config = ObservabilityConfig.testing()
        else:
            # Development: Console + File
            config = ObservabilityConfig.development()

        # Create exporter and registry
        exporter = create_exporter_from_config(config)
        return MetricsRegistry(exporter=exporter)

    def _add_sample_data(self):
        """Add sample entities to the graph."""
        nike = Entity(
            entity_id="brand:nike",
            entity_type="brand",
            name="Nike",
            properties={"founded": 1964, "headquarters": "Beaverton, Oregon"},
        )
        adidas = Entity(
            entity_id="brand:adidas",
            entity_type="brand",
            name="Adidas",
            properties={"founded": 1949, "headquarters": "Herzogenaurach, Germany"},
        )

        self.graph.add_entity(nike)
        self.graph.add_entity(adidas)

        # Track metrics
        self.registry.counter("entities_created_total", tags={"type": "brand"})
        self.registry.gauge("entity_count", 2, tags={"type": "brand"})


# ============================================================================
# HTTP Handlers
# ============================================================================

async def metrics_handler(request: web.Request) -> web.Response:
    """
    Serve Prometheus metrics for scraping.

    Endpoint: GET /metrics

    This endpoint is scraped by Prometheus/Alloy.
    """
    app = request.app["app"]

    # Get the HTTP exporter from the registry
    exporter = app.registry._exporter

    if isinstance(exporter, CompositeExporter):
        # Find the HTTP exporter in the composite
        for exp in exporter.exporters:
            if isinstance(exp, PrometheusHTTPExporter):
                metrics_text = exp.get_metrics_text()
                return web.Response(
                    text=metrics_text,
                    content_type="text/plain; version=0.0.4; charset=utf-8",
                )

    # Fallback: Format metrics directly
    from autoflow.context_graph.observability import format_prometheus_metrics
    metrics_text = format_prometheus_metrics(app.registry)

    return web.Response(
        text=metrics_text,
        content_type="text/plain; version=0.0.4; charset=utf-8",
    )


async def health_handler(request: web.Request) -> web.Response:
    """
    Health check endpoint.

    Endpoint: GET /health
    """
    return web.json_response({
        "status": "healthy",
        "uptime": "1h 23m",
    })


async def entities_handler(request: web.Request) -> web.Response:
    """
    API endpoint for querying entities.

    Endpoint: GET /api/entities

    Demonstrates automatic instrumentation.
    """
    app = request.app["app"]
    entity_id = request.query.get("id")

    if entity_id:
        entity = app.graph.get_entity(entity_id)
        if entity:
            # Track success metric
            app.registry.counter("api_requests_total", tags={
                "endpoint": "/api/entities",
                "status": "200",
            })
            return web.json_response(entity.model_dump())
        else:
            # Track not found
            app.registry.counter("api_requests_total", tags={
                "endpoint": "/api/entities",
                "status": "404",
            })
            return web.json_response({"error": "Not found"}, status=404)
    else:
        # List all entities
        entities = app.graph.entities
        app.registry.counter("api_requests_total", tags={
            "endpoint": "/api/entities",
            "status": "200",
        })
        return web.json_response({
            "entities": [e.model_dump() for e in entities],
            "count": len(entities),
        })


# ============================================================================
# Server Setup
# ============================================================================

def create_app() -> web.Application:
    """
    Create the aiohttp application.

    Returns:
        Configured application
    """
    # Create application instance
    app_instance = Application()

    # Setup aiohttp app
    app = web.Application()
    app["app"] = app_instance

    # Register routes
    app.router.add_get("/metrics", metrics_handler)
    app.router.add_get("/health", health_handler)
    app.router.add_get("/api/entities", entities_handler)

    return app


def main():
    """Run the server."""
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Create app
    app = create_app()

    # Get port from environment or use default
    port = int(os.getenv("PORT", "9090"))

    logger.info(f"Starting Context Graph API server on port {port}")
    logger.info(f"Metrics available at: http://localhost:{port}/metrics")
    logger.info(f"Health check at: http://localhost:{port}/health")
    logger.info(f"Entities API at: http://localhost:{port}/api/entities")

    # Run server
    web.run_app(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
