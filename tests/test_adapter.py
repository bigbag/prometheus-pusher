from unittest.mock import Mock, patch

import pytest
from prometheus_client import CollectorRegistry

from prometheus_pusher import MonitoringAdapter
from prometheus_pusher._producer import EmptyProducer, Producer


def test_send_serve_and_shutdown_require_startup() -> None:
    adapter = MonitoringAdapter()

    with pytest.raises(RuntimeError, match=r"Call startup\(\) first"):
        adapter.send()
    with pytest.raises(RuntimeError, match=r"Call startup\(\) first"):
        adapter.serve()
    with pytest.raises(RuntimeError, match=r"Call startup\(\) first"):
        adapter.shutdown()


def test_startup_preserves_enabled_and_disabled_producer_selection() -> None:
    adapter = MonitoringAdapter()
    registry = CollectorRegistry()

    adapter.startup("http://localhost:9091", "demo", registry, is_enabled=True)
    assert adapter.is_enabled is True
    assert isinstance(adapter._producer, Producer)

    adapter.startup("http://localhost:9091", "demo", registry, is_enabled=False)
    assert adapter.is_enabled is False
    assert isinstance(adapter._producer, EmptyProducer)


@patch("prometheus_pusher._adapter.threading.Thread")
def test_serve_starts_one_daemon_worker_until_shutdown(thread_type: Mock) -> None:
    thread = thread_type.return_value
    thread.is_alive.return_value = True
    adapter = MonitoringAdapter()
    adapter.startup("http://localhost:9091", "demo", CollectorRegistry(), is_enabled=True)

    adapter.serve(2)
    adapter.serve(2)

    thread_type.assert_called_once()
    assert thread_type.call_args.kwargs["daemon"] is True
    thread.start.assert_called_once()


def test_shutdown_signals_and_joins_the_adapter_worker() -> None:
    adapter = MonitoringAdapter()
    adapter.startup("http://localhost:9091", "demo", CollectorRegistry())
    worker = Mock()
    worker.is_alive.return_value = True
    stop_event = Mock()
    adapter._worker = worker
    adapter._stop_event = stop_event

    adapter.shutdown(timeout=1.5)

    stop_event.set.assert_called_once_with()
    worker.join.assert_called_once_with(1.5)


@patch("prometheus_pusher._adapter.threading.Thread")
def test_serve_after_shutdown_uses_a_fresh_unset_stop_event(thread_type: Mock) -> None:
    adapter = MonitoringAdapter()
    adapter.startup("http://localhost:9091", "demo", CollectorRegistry())
    previous_event = adapter._stop_event

    adapter.shutdown()
    adapter.serve()

    current_event = thread_type.call_args.kwargs["args"][0]
    assert current_event is not previous_event
    assert current_event.is_set() is False


@patch("prometheus_pusher._adapter.threading.Thread")
@pytest.mark.parametrize("timeout", [0, -1])
def test_serve_rejects_non_positive_worker_timeouts(thread_type: Mock, timeout: int) -> None:
    adapter = MonitoringAdapter()
    adapter.startup("http://localhost:9091", "demo", CollectorRegistry())

    with pytest.raises(ValueError, match="worker_timeout must be greater than zero"):
        adapter.serve(timeout)

    thread_type.assert_not_called()


def test_disabled_adapter_send_is_a_no_op() -> None:
    adapter = MonitoringAdapter()
    adapter.startup("http://localhost:9091", "demo", CollectorRegistry(), is_enabled=False)

    with patch.object(EmptyProducer, "send") as send:
        adapter.send()

    send.assert_called_once_with()


def test_shutdown_only_signals_the_owning_adapter_event() -> None:
    first = MonitoringAdapter()
    second = MonitoringAdapter()
    registry = CollectorRegistry()
    first.startup("http://localhost:9091", "first", registry)
    second.startup("http://localhost:9091", "second", registry)
    first_event = first._stop_event
    second_event = second._stop_event

    first.shutdown()

    assert first_event is not None and first_event.is_set() is True
    assert second_event is not None and second_event.is_set() is False


def test_startup_stops_the_previous_worker_before_replacing_the_producer() -> None:
    adapter = MonitoringAdapter()
    registry = CollectorRegistry()
    adapter.startup("http://localhost:9091", "first", registry)
    previous_worker = Mock()
    previous_worker.is_alive.return_value = True
    adapter._worker = previous_worker

    adapter.startup("http://localhost:9091", "second", registry)

    previous_worker.join.assert_called_once_with(None)
    assert adapter._producer is not None
    assert adapter._producer.job_name == "second"
