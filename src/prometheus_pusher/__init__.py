"""Lifecycle-safe Prometheus Pushgateway metric publishing."""

from ._adapter import MonitoringAdapter, monitoring_adapter
from ._producer import Producer

__version__ = "1.0.0"

__all__ = ["MonitoringAdapter", "Producer", "monitoring_adapter", "__version__"]
