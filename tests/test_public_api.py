import inspect

import prometheus_pusher as package
from prometheus_pusher import helper


def test_package_exports_the_supported_1_0_api() -> None:
    assert package.__version__ == "1.0.0"
    assert package.__all__ == [
        "MonitoringAdapter",
        "Producer",
        "monitoring_adapter",
        "__version__",
    ]
    assert package.Producer is helper.Producer
    assert package.MonitoringAdapter is helper.MonitoringAdapter


def test_legacy_adapter_method_signatures_are_preserved() -> None:
    assert list(inspect.signature(package.MonitoringAdapter.startup).parameters) == [
        "self",
        "gateway",
        "job_name",
        "registry",
        "user",
        "password",
        "ssl_verify",
        "is_enabled",
    ]
    assert list(inspect.signature(package.MonitoringAdapter.serve).parameters) == [
        "self",
        "worker_timeout",
    ]
    assert list(inspect.signature(package.MonitoringAdapter.send).parameters) == ["self"]
    assert list(inspect.signature(package.MonitoringAdapter.shutdown).parameters) == [
        "self",
        "timeout",
    ]
