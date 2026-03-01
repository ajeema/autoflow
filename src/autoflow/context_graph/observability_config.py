"""
Configuration system for Context Graph Framework observability.

Provides easy setup for different exporters and configurations.
"""

from typing import Any, Optional, List
import logging

from pydantic import BaseModel, Field, ConfigDict, field_validator

logger = logging.getLogger(__name__)

# Import exporters
from autoflow.context_graph.observability_exporters import (
    Exporter,
    CompositeExporter,
    PrometheusFileExporter,
    PrometheusHTTPExporter,
    OTLPExporter,
    OTLPHTTPExporter,
    ConsoleExporter,
)


class ObservabilityConfig(BaseModel):
    """
    Configuration for observability system.

    Supports multiple exporters and flexible configuration.
    """

    model_config = ConfigDict(
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )

    # Metrics configuration
    metrics_enabled: bool = True
    metrics_export_interval_seconds: float = 60.0

    # Tracing configuration
    tracing_enabled: bool = True
    trace_exporter_enabled: bool = False

    # Exporters (set automatically or provide custom)
    exporters: List[Exporter] = Field(default_factory=list)

    # Prometheus file exporter
    prometheus_file_path: Optional[str] = None

    # OTLP exporter (for Alloy, OTEL Collector, Grafana)
    otlp_endpoint: Optional[str] = None
    otlp_headers: dict[str, str] = Field(default_factory=dict)
    otlp_insecure: bool = True

    # Console exporter (for debugging)
    console_enabled: bool = False

    # Performance tracking
    performance_tracker_window_seconds: int = 60
    performance_tracker_max_windows: int = 1440  # 24 hours at 60s windows

    # Health checks
    health_check_timeout_seconds: float = 5.0

    def model_post_init(self, __context: Any) -> None:
        """Initialize exporters based on configuration."""
        # If no exporters provided, create them from config
        if not self.exporters:
            self.exporters = self._create_exporters()

    def _create_exporters(self) -> List[Exporter]:
        """Create exporters from configuration."""
        exporters = []

        # Prometheus file exporter
        if self.prometheus_file_path:
            exporters.append(
                PrometheusFileExporter(
                    filepath=self.prometheus_file_path,
                    enabled=self.metrics_enabled,
                )
            )
            logger.info(f"Configured Prometheus file exporter: {self.prometheus_file_path}")

        # OTLP exporter
        if self.otlp_endpoint:
            exporters.append(
                OTLPExporter(
                    endpoint=self.otlp_endpoint,
                    headers=self.otlp_headers,
                    enabled=self.metrics_enabled,
                    insecure=self.otlp_insecure,
                )
            )
            logger.info(f"Configured OTLP exporter: {self.otlp_endpoint}")

        # Console exporter (for debugging)
        if self.console_enabled:
            exporters.append(ConsoleExporter(enabled=self.metrics_enabled))
            logger.info("Configured console exporter")

        return exporters

    @classmethod
    def development(cls) -> "ObservabilityConfig":
        """
        Development configuration - console output + file.

        Useful for local development and debugging.
        """
        return cls(
            prometheus_file_path="/tmp/metrics.prom",
            console_enabled=True,
            metrics_enabled=True,
            tracing_enabled=True,
        )

    @classmethod
    def testing(cls) -> "ObservabilityConfig":
        """
        Testing configuration - minimal overhead.
        """
        return cls(
            prometheus_file_path="/tmp/test_metrics.prom",
            console_enabled=False,
            metrics_enabled=True,
            tracing_enabled=False,
        )

    @classmethod
    def production_grafana_cloud(
        cls,
        instance_url: str,
        api_key: str,
        metrics_file: Optional[str] = None,
    ) -> "ObservabilityConfig":
        """
        Production configuration for Grafana Cloud.

        Args:
            instance_url: Grafana Cloud instance URL (e.g., https://your-instance.grafana.net)
            api_key: Grafana API key with metrics:write scope
            metrics_file: Optional local metrics file for backup/scraping
        """
        # Grafana Cloud OTLP endpoint
        otlp_endpoint = f"{instance_url.replace('https://', 'https://otlp.')}/otlp"

        return cls(
            otlp_endpoint=otlp_endpoint,
            otlp_headers={"Authorization": f"Bearer {api_key}"},
            otlp_insecure=False,
            prometheus_file_path=metrics_file,
            console_enabled=False,
            metrics_enabled=True,
            tracing_enabled=True,
        )

    @classmethod
    def production_alloy(
        cls,
        alloy_endpoint: str = "http://localhost:4318",
        metrics_file: Optional[str] = None,
    ) -> "ObservabilityConfig":
        """
        Production configuration for Alloy (local or self-hosted).

        Args:
            alloy_endpoint: Alloy OTLP endpoint (default: http://localhost:4318)
            metrics_file: Optional local metrics file for Prometheus scraping
        """
        return cls(
            otlp_endpoint=alloy_endpoint,
            otlp_insecure=True,
            prometheus_file_path=metrics_file,  # For scraping by Alloy
            console_enabled=False,
            metrics_enabled=True,
            tracing_enabled=True,
        )

    @classmethod
    def production_prometheus(
        cls,
        metrics_file: str = "/var/lib/node_exporter/textfile_collector/context_graph.prom",
    ) -> "ObservabilityConfig":
        """
        Production configuration for Prometheus scraping.

        Args:
            metrics_file: Path for node_exporter textfile collector
        """
        return cls(
            prometheus_file_path=metrics_file,
            console_enabled=False,
            metrics_enabled=True,
            tracing_enabled=False,  # Prometheus doesn't handle traces
        )

    @classmethod
    def custom(
        cls,
        exporters: List[Exporter],
        **kwargs,
    ) -> "ObservabilityConfig":
        """
        Custom configuration with user-provided exporters.

        Args:
            exporters: List of configured exporters
            **kwargs: Additional configuration options
        """
        return cls(
            exporters=exporters,
            **kwargs,
        )


def create_exporter_from_config(config: ObservabilityConfig) -> Exporter:
    """
    Create a composite exporter from configuration.

    Args:
        config: Observability configuration

    Returns:
        Configured exporter (or CompositeExporter for multiple)
    """
    exporters = config._create_exporters()

    if len(exporters) == 0:
        # No exporters configured, use no-op exporter
        logger.warning("No exporters configured, metrics will not be exported")
        return ConsoleExporter(enabled=False)
    elif len(exporters) == 1:
        return exporters[0]
    else:
        return CompositeExporter(exporters)
