import runpy
from unittest.mock import patch


def test_basic_usage_example_stops_the_worker() -> None:
    with (
        patch("prometheus_pusher.MonitoringAdapter.send"),
        patch("prometheus_pusher.MonitoringAdapter.serve"),
        patch("prometheus_pusher.MonitoringAdapter.shutdown") as shutdown,
    ):
        runpy.run_path("examples/basic_usage.py", run_name="__main__")

    shutdown.assert_called_once()
