"""Prometheus Pushgateway transport and producer implementations."""

from __future__ import annotations

import base64
import logging
import ssl
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.request import HTTPSHandler, Request, build_opener

from prometheus_client import CollectorRegistry, push_to_gateway

logger = logging.getLogger(__name__)


def _get_ssl_handler(verify: bool = True) -> HTTPSHandler:
    context = ssl.create_default_context()
    if not verify:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return HTTPSHandler(context=context)


def _get_basic_auth_header(user: str, password: str) -> tuple[str, bytes]:
    token = base64.b64encode(f"{user}:{password}".encode())
    return "Authorization", b"Basic " + token


@dataclass
class BaseProducer:
    """Common configuration for enabled and disabled producers."""

    gateway: str
    registry: CollectorRegistry
    job_name: str = "job_name"
    user: str | None = ""
    password: str | None = ""
    ssl_verify: bool = False

    def send(self) -> None:
        """Send a metrics update; the base implementation is a no-op."""

    def run_worker(self, stop_event: threading.Event, timeout: float) -> None:
        """Run a no-op worker; subclasses provide the scheduling behavior."""


class EmptyProducer(BaseProducer):
    """Producer used when monitoring is disabled."""

    def run_worker(self, stop_event: threading.Event, timeout: float) -> None:
        while not stop_event.wait(timeout):
            pass


class Producer(BaseProducer):
    """Push metrics to a Prometheus Pushgateway."""

    def _push_to_gateway(self) -> None:
        def custom_handler(
            url: str,
            method: str,
            timeout: float | None,
            headers: Sequence[tuple[str, Any]],
            data: bytes,
        ) -> Callable[[], None]:
            request_headers = list(headers)
            if self.user and self.password:
                request_headers.append(_get_basic_auth_header(self.user, self.password))

            def handler() -> None:
                request = Request(url, data=data, method=method)
                for key, value in request_headers:
                    request.add_header(key, value)
                with build_opener(_get_ssl_handler(self.ssl_verify)).open(
                    request, timeout=timeout
                ) as response:
                    if response.getcode() >= 400:
                        logger.warning(
                            "Pushgateway metrics push failed for %s: %s",
                            response.geturl(),
                            response.info(),
                        )

            return handler

        try:
            push_to_gateway(
                gateway=self.gateway,
                job=self.job_name,
                registry=self.registry,
                handler=custom_handler,
            )
        except URLError:
            logger.error("Unable to push metrics to Pushgateway %s", self.gateway)
        except Exception:
            logger.exception("Unable to push metrics to Pushgateway %s", self.gateway)

    def send(self) -> None:
        self._push_to_gateway()

    def run_worker(self, stop_event: threading.Event, timeout: float) -> None:
        while not stop_event.is_set():
            self.send()
            if stop_event.wait(timeout):
                break
