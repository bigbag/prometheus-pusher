"""Push a metric immediately, then start periodic Pushgateway publishing."""

from prometheus_client import CollectorRegistry, Counter

from prometheus_pusher import monitoring_adapter

registry = CollectorRegistry()
requests = Counter("demo_requests_total", "Number of demo requests", registry=registry)

monitoring_adapter.startup(
    gateway="http://127.0.0.1:9091",
    job_name="demo",
    registry=registry,
    is_enabled=True,
)

try:
    requests.inc()
    monitoring_adapter.send()
    monitoring_adapter.serve(worker_timeout=10)
finally:
    monitoring_adapter.shutdown()
