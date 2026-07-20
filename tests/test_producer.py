import ssl
from unittest.mock import Mock, patch
from urllib.error import URLError

import pytest
from prometheus_client import CollectorRegistry

from prometheus_pusher._producer import (
    EmptyProducer,
    Producer,
    _get_basic_auth_header,
    _get_ssl_handler,
)


def test_basic_auth_header_encodes_credentials() -> None:
    assert _get_basic_auth_header("testuser", "testpass") == (
        "Authorization",
        b"Basic dGVzdHVzZXI6dGVzdHBhc3M=",
    )


def test_disabled_producer_never_pushes() -> None:
    producer = EmptyProducer(gateway="http://localhost:9091", registry=CollectorRegistry())
    producer.send()


@patch("prometheus_pusher._producer.push_to_gateway")
def test_producer_pushes_with_its_gateway_job_and_registry(mock_push: Mock) -> None:
    registry = CollectorRegistry()
    producer = Producer(gateway="http://localhost:9091", registry=registry, job_name="demo")

    producer.send()

    assert mock_push.call_args.kwargs["gateway"] == "http://localhost:9091"
    assert mock_push.call_args.kwargs["job"] == "demo"
    assert mock_push.call_args.kwargs["registry"] is registry
    assert callable(mock_push.call_args.kwargs["handler"])


@patch("prometheus_pusher._producer.push_to_gateway", side_effect=OSError("offline"))
def test_producer_logs_and_suppresses_unexpected_push_errors(mock_push: Mock, caplog) -> None:
    producer = Producer(gateway="http://localhost:9091", registry=CollectorRegistry())

    producer.send()

    assert "Unable to push metrics to Pushgateway http://localhost:9091" in caplog.text
    mock_push.assert_called_once()


def test_enabled_worker_sends_immediately_then_stops_when_event_is_set() -> None:
    producer = Producer(gateway="http://localhost:9091", registry=CollectorRegistry())
    producer.send = Mock()  # type: ignore[method-assign]
    stop_event = Mock()
    stop_event.is_set.return_value = False
    stop_event.wait.return_value = True

    producer.run_worker(stop_event, 10)

    producer.send.assert_called_once()
    stop_event.wait.assert_called_once_with(10)


@patch("prometheus_pusher._producer.build_opener")
def test_custom_handler_adds_auth_without_mutating_caller_headers(opener: Mock) -> None:
    producer = Producer(
        gateway="https://localhost:9091",
        registry=CollectorRegistry(),
        user="user",
        password="password",
        ssl_verify=True,
    )

    with patch("prometheus_pusher._producer.push_to_gateway") as push:
        producer.send()
        handler = push.call_args.kwargs["handler"]
        headers = [("X-Test", "value")]
        request_callable = handler("https://localhost", "PUT", 3, headers, b"data")
        response = opener.return_value.open.return_value
        response.__enter__.return_value.getcode.return_value = 200
        request_callable()

    assert headers == [("X-Test", "value")]
    request = opener.return_value.open.call_args.args[0]
    assert request.get_header("Authorization") == b"Basic dXNlcjpwYXNzd29yZA=="


def test_ssl_handler_disables_hostname_and_certificate_checks() -> None:
    handler = _get_ssl_handler(verify=False)

    assert handler._context.check_hostname is False
    assert handler._context.verify_mode == ssl.CERT_NONE


def test_ssl_handler_keeps_default_verification() -> None:
    handler = _get_ssl_handler(verify=True)

    assert handler._context.check_hostname is True
    assert handler._context.verify_mode == ssl.CERT_REQUIRED


@patch("prometheus_pusher._producer.build_opener")
def test_custom_handler_omits_auth_when_credentials_are_incomplete(opener: Mock) -> None:
    producer = Producer(
        gateway="https://localhost:9091",
        registry=CollectorRegistry(),
        user="user",
        password=None,
    )

    with patch("prometheus_pusher._producer.push_to_gateway") as push:
        producer.send()
        handler = push.call_args.kwargs["handler"]
        request_callable = handler("https://localhost", "PUT", 3, [], b"data")
        opener.return_value.open.return_value.__enter__.return_value.getcode.return_value = 200
        request_callable()

    request = opener.return_value.open.call_args.args[0]
    assert request.get_header("Authorization") is None


@patch("prometheus_pusher._producer.build_opener")
def test_custom_handler_logs_http_failure_status(
    opener: Mock, caplog: pytest.LogCaptureFixture
) -> None:
    producer = Producer(gateway="https://localhost:9091", registry=CollectorRegistry())
    response = opener.return_value.open.return_value.__enter__.return_value
    response.getcode.return_value = 503
    response.geturl.return_value = "https://localhost:9091/metrics"
    response.info.return_value = "service unavailable"

    with patch("prometheus_pusher._producer.push_to_gateway") as push:
        producer.send()
        handler = push.call_args.kwargs["handler"]
        handler("https://localhost", "PUT", 3, [], b"data")()

    assert "Pushgateway metrics push failed for https://localhost:9091/metrics" in caplog.text


@patch("prometheus_pusher._producer.push_to_gateway", side_effect=URLError("offline"))
def test_producer_logs_and_suppresses_url_errors(
    mock_push: Mock, caplog: pytest.LogCaptureFixture
) -> None:
    producer = Producer(gateway="https://localhost:9091", registry=CollectorRegistry())

    producer.send()

    assert "Unable to push metrics to Pushgateway https://localhost:9091" in caplog.text
    mock_push.assert_called_once()
