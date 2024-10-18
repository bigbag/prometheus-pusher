import base64
import logging
import ssl
import threading
import time
from dataclasses import dataclass
from typing import Any, Optional, Sequence, Tuple
from urllib.error import URLError
from urllib.request import HTTPSHandler, Request, build_opener

from prometheus_client import CollectorRegistry, push_to_gateway

logger = logging.getLogger(__name__)

stop_event = threading.Event()


def _get_ssl_handler(verify: bool = True) -> HTTPSHandler:
    ssl_context = ssl.create_default_context()
    if not verify:
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

    return HTTPSHandler(context=ssl_context)


def _get_basic_auth_header(user: str, password: str) -> Tuple[str, bytes]:
    auth_token = base64.b64encode(f"{user}:{password}".encode())
    return ("Authorization", b"Basic " + auth_token)


@dataclass
class BaseProducer:
    gateway: str
    registry: CollectorRegistry
    job_name: str = "job_name"
    user: str = ""
    password: str = ""
    ssl_verify: bool = False

    def send(self) -> None:
        pass

    def run_worker(self, stop_event: threading.Event, timeout: int) -> None:
        pass


class EmptyProducer(BaseProducer):
    def run_worker(self, stop_event: threading.Event, timeout: int) -> None:
        while not stop_event.is_set():
            time.sleep(timeout)


class Producer(BaseProducer):
    def _push_to_gateway(self):
        def custom_handler(
            url: str,
            method: str,
            timeout: Optional[float],
            headers: Sequence[Tuple[str, Any]],
            data: bytes,
        ):
            def handler():
                request = Request(url, data=data)
                if self.user and self.password:
                    headers.append(_get_basic_auth_header(self.user, self.password))

                request.get_method = lambda: method
                for k, v in headers:
                    request.add_header(k, v)

                response = build_opener(_get_ssl_handler(verify=self.ssl_verify)).open(
                    request, timeout=timeout
                )
                if response.getcode() >= 400:
                    error_url = response.geturl()
                    error_info = response.info()
                    logger.warning(f"Pushgateway metrics push failed. {error_url} {error_info}")

            return handler

        try:
            push_to_gateway(
                gateway=self.gateway,
                job=self.job_name,
                registry=self.registry,
                handler=custom_handler,
            )
        except URLError:
            logger.error(f"Unable to connect to the prometeus service: {self.gateway}!")
        except Exception as exc:
            logger.error(exc)

    def send(self):
        self._push_to_gateway()

    def run_worker(self, stop_event: threading.Event, timeout: int):
        while not stop_event.is_set():
            self._push_to_gateway()
            time.sleep(timeout)


class MonitoringAdapter:
    def __init__(self):
        self.is_enabled = False

    def __getattribute__(self, name):
        try:
            return object.__getattribute__(self, name)
        except AttributeError as exc:
            if name in ["_producer"]:
                raise AttributeError("MonitoringAdapter not initialized. Call startup() first.")
            raise exc

    def startup(
        self,
        gateway: str,
        job_name: str,
        registry: CollectorRegistry,
        user: str = "",  # nosec
        password: str = "",  # nosec
        ssl_verify: bool = False,
        is_enabled: bool = False,
    ) -> None:
        self.is_enabled = is_enabled

        producer_class = Producer if is_enabled else EmptyProducer

        self._producer = producer_class(
            gateway=gateway,
            registry=registry,
            job_name=job_name,
            user=user,
            password=password,
            ssl_verify=ssl_verify,
        )

    def serve(self, worker_timeout: int = 10) -> None:
        worker = threading.Thread(
            target=self._producer.run_worker,
            args=(stop_event, worker_timeout),
        )
        worker.start()

    def send(self) -> None:
        self._producer.send()


monitoring_adapter = MonitoringAdapter()
