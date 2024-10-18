# prometheus-pusher

[![CI](https://github.com/bigbag/prometheus-pusher/workflows/CI/badge.svg)](https://github.com/bigbag/prometheus-pusher/actions?query=workflow%3ACI)
[![codecov](https://codecov.io/gh/bigbag/prometheus-pusher/branch/main/graph/badge.svg?token=ZRUN7SUKB2)](https://codecov.io/gh/bigbag/prometheus-pusher)
[![pypi](https://img.shields.io/pypi/v/prometheus-pusher.svg)](https://pypi.python.org/pypi/prometheus-pusher)
[![downloads](https://img.shields.io/pypi/dm/prometheus-pusher.svg)](https://pypistats.org/packages/prometheus-pusher)
[![versions](https://img.shields.io/pypi/pyversions/prometheus-pusher.svg)](https://github.com/bigbag/prometheus-pusher)
[![license](https://img.shields.io/github/license/bigbag/prometheus-pusher.svg)](https://github.com/bigbag/prometheus-pusher/blob/master/LICENSE)


**prometheus-pusher** is a helper for push metrics in Prometheus push gateway.

* [Project Changelog](CHANGELOG.md)

## Installation

prometheus-pusher is available on PyPI.
Use pip to install:

    $ pip install prometheus-pusher

## Basic Usage

```py
from prometheus_client import CollectorRegistry
from prometheus_client import Counter

from prometheus_pusher import monitoring_adapter

monitoring_registry = CollectorRegistry()
demo_count_metric = Counter("demo", "Demo count", registry=monitoring_registry)


monitoring_adapter.startup(
    gateway="http://127.0.0.1:9091",
    job_name="test_job",
    user="testuser",
    password="testpassword",
    registry=monitoring_registry,
    is_enabled=True,
)


def demo_send():
    demo_count_metric.inc()
    monitoring_adapter.send()
    return


def demo_serve():
    demo_count_metric.inc()
    monitoring_adapter.serve()
    return


if __name__ == "__main__":
    demo_send()
    demo_serve()
    print("Test")
    
```

## License

prometheus-pusher is developed and distributed under the Apache 2.0 license.

## Reporting a Security Vulnerability

See our [security policy](https://github.com/bigbag/prometheus-pusher/security/policy).
