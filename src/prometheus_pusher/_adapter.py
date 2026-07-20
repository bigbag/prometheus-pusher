"""Adapter lifecycle management for Pushgateway producers."""

from __future__ import annotations

import threading
from typing import Final

from prometheus_client import CollectorRegistry

from ._producer import EmptyProducer, Producer

_NOT_INITIALIZED: Final = "MonitoringAdapter not initialized. Call startup() first."


class MonitoringAdapter:
    """Configure, push, and periodically publish a metrics registry."""

    def __init__(self) -> None:
        self.is_enabled = False
        self._producer: Producer | EmptyProducer | None = None
        self._stop_event: threading.Event | None = None
        self._worker: threading.Thread | None = None
        self._lock = threading.Lock()

    def _require_producer(self) -> Producer | EmptyProducer:
        if self._producer is None:
            raise RuntimeError(_NOT_INITIALIZED)
        return self._producer

    def startup(
        self,
        gateway: str,
        job_name: str,
        registry: CollectorRegistry,
        user: str | None = "",
        password: str | None = "",
        ssl_verify: bool = False,
        is_enabled: bool = False,
    ) -> None:
        if self._producer is not None:
            self.shutdown()

        producer_type = Producer if is_enabled else EmptyProducer
        with self._lock:
            self.is_enabled = is_enabled
            self._producer = producer_type(
                gateway=gateway,
                registry=registry,
                job_name=job_name,
                user=user,
                password=password,
                ssl_verify=ssl_verify,
            )
            self._stop_event = threading.Event()
            self._worker = None

    def serve(self, worker_timeout: int = 10) -> None:
        """Start periodic publishing unless this adapter already has a live worker."""
        if worker_timeout <= 0:
            raise ValueError("worker_timeout must be greater than zero")

        with self._lock:
            producer = self._require_producer()
            if self._worker is not None and self._worker.is_alive():
                return

            stop_event = self._stop_event
            if stop_event is None:
                raise RuntimeError(_NOT_INITIALIZED)
            if stop_event.is_set():
                stop_event = threading.Event()
                self._stop_event = stop_event

            self._worker = threading.Thread(
                target=producer.run_worker,
                args=(stop_event, worker_timeout),
                name="prometheus-pusher",
                daemon=True,
            )
            self._worker.start()

    def send(self) -> None:
        """Push the configured registry once."""
        self._require_producer().send()

    def shutdown(self, timeout: float | None = None) -> None:
        """Signal and join this adapter's worker, if it has been started."""
        with self._lock:
            self._require_producer()
            stop_event = self._stop_event
            worker = self._worker
            self._worker = None

        if stop_event is not None:
            stop_event.set()
        if worker is not None and worker.is_alive():
            worker.join(timeout)


monitoring_adapter = MonitoringAdapter()
