# prometheus-pusher

A lifecycle-safe helper for pushing application metrics to a Prometheus Pushgateway.

## Requirements

Python 3.11 or newer. CI validates Python 3.11, 3.12, 3.13, and 3.14.

## Install

```console
uv add prometheus-pusher
```

```console
pip install prometheus-pusher
```

## Usage

```python
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
    monitoring_adapter.send()  # Push immediately.
    monitoring_adapter.serve(worker_timeout=10)  # Then push every 10 seconds.
finally:
    monitoring_adapter.shutdown()
```

`startup()` configures the adapter. `send()` performs one push. `serve()` starts one daemon worker and is idempotent while that worker is alive. `shutdown()` signals and joins the adapter-owned worker; call it during application shutdown. A disabled adapter (`is_enabled=False`) remains a no-op.

Pass `user` and `password` for HTTP Basic authentication. Set `ssl_verify=True` for HTTPS endpoints with certificate verification; `ssl_verify=False` disables certificate validation and should be used only for trusted development environments. Push and network failures are logged and do not interrupt application execution.

## Migrating from 0.1.0

1. Upgrade the application to Python 3.11 or newer.
2. Retain existing `monitoring_adapter.startup(...)`, `send()`, and `serve()` calls.
3. Add `monitoring_adapter.shutdown()` to the application's graceful-shutdown path.

Version 1.0.0 replaces the global, never-stopped worker with lifecycle owned by each `MonitoringAdapter` instance.

## Development

```console
uv sync --all-groups
uv run ruff format --check src tests examples
uv run ruff check src tests examples
uv run mypy src
uv run pytest --cov=prometheus_pusher
uv build
```

## License and security

Distributed under the Apache License 2.0. See the [security policy](https://github.com/bigbag/prometheus-pusher/security/policy) to report vulnerabilities.
