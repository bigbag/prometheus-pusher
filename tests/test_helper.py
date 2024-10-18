from unittest.mock import Mock, patch

import pytest
from prometheus_client import CollectorRegistry

from prometheus_pusher.helper import (
    BaseProducer,
    EmptyProducer,
    MonitoringAdapter,
    Producer,
    _get_basic_auth_header,
)


@pytest.fixture
def registry():
    return CollectorRegistry()


@pytest.fixture
def adapter():
    return MonitoringAdapter()


def test_get_basic_auth_header():
    user = "testuser"
    password = "testpass"
    header_name, header_value = _get_basic_auth_header(user, password)

    assert header_name == "Authorization"
    assert header_value == b"Basic dGVzdHVzZXI6dGVzdHBhc3M="


def test_startup_enabled(adapter, registry):
    adapter.startup(
        gateway="http://localhost:9091", job_name="test_job", registry=registry, is_enabled=True
    )
    assert adapter.is_enabled
    assert isinstance(adapter._producer, Producer)


def test_startup_disabled(adapter, registry):
    adapter.startup(
        gateway="http://localhost:9091", job_name="test_job", registry=registry, is_enabled=False
    )
    assert not adapter.is_enabled
    assert isinstance(adapter._producer, EmptyProducer)


def test_serve_not_initialized(adapter):
    with pytest.raises(AttributeError):
        adapter.serve()


def test_send_not_initialized(adapter):
    with pytest.raises(AttributeError):
        adapter.send()


def test_attribute_not_initialized(adapter):
    with pytest.raises(AttributeError):
        adapter.demo


@patch("threading.Thread")
def test_serve(mock_thread, adapter, registry):
    adapter.startup(
        gateway="http://localhost:9091", job_name="test_job", registry=registry, is_enabled=True
    )
    adapter.serve()
    mock_thread.assert_called_once()


@patch.object(Producer, "send")
def test_send(mock_send, adapter, registry):
    adapter.startup(
        gateway="http://localhost:9091", job_name="test_job", registry=registry, is_enabled=True
    )
    adapter.send()
    mock_send.assert_called_once()


@patch("time.sleep")
def test_producer(mock_sleep, registry):
    producer = Producer(gateway="http://localhost:9091", registry=registry, job_name="test_job")
    stop_event = Mock()
    stop_event.is_set.side_effect = [False, True]
    producer.run_worker(stop_event, 10)
    producer.send()
    mock_sleep.assert_called_once_with(10)


@patch("prometheus_pusher.helper._get_basic_auth_header")
@patch("time.sleep")
def test_producer_with_auth(mock_sleep, mock_get_basic_auth_header, registry):
    producer = Producer(
        gateway="http://localhost:9091",
        registry=registry,
        job_name="test_job",
        user="testuser",
        password="testpass",
    )
    producer.run_worker(Mock(), 10)
    producer.send()
    mock_get_basic_auth_header.assert_called_once_with("testuser", "testpass")


@patch("time.sleep")
def test_empty_producer_run_worker(mock_sleep):
    producer = EmptyProducer(gateway="http://localhost:9091", registry=Mock(), job_name="test_job")
    stop_event = Mock()
    stop_event.is_set.side_effect = [False, True]
    producer.send()
    producer.run_worker(stop_event, 10)
    mock_sleep.assert_called_once_with(10)


def test_base_producer_run_worker():
    producer = BaseProducer(gateway="http://localhost:9091", registry=Mock(), job_name="test_job")
    producer.send()
    producer.run_worker(Mock(), 10)


@patch("prometheus_pusher.helper.build_opener")
@patch("prometheus_pusher.helper.logger")
def test_custom_handler_error_logging(mock_logger, mock_build_opener, registry):
    mock_response = Mock()
    mock_response.getcode.return_value = 400
    mock_response.geturl.return_value = "http://example.com"
    mock_response.info.return_value = "Error info"
    mock_build_opener.return_value.open.return_value = mock_response

    producer = Producer(gateway="http://localhost:9091", registry=registry, job_name="test_job")
    producer.send()

    mock_logger.warning.assert_called_once_with(
        "Pushgateway metrics push failed. {} {}".format("http://example.com", "Error info")
    )
