"""Kafka -> ClickHouse : ingestion par micro-lots des flux d'événements."""
from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from typing import Any

from app import bus
from app.config import Topics
from app.stores import ch

log = logging.getLogger("ingest")


class Ingestor(threading.Thread):
    def __init__(self, flush_seconds: float = 0.5) -> None:
        super().__init__(daemon=True, name="ingest")
        self.flush_seconds = flush_seconds
        self.rows_ingested = 0

    def run(self) -> None:
        consumer = bus.consumer(Topics.INGESTED.keys(), group_id="clickhouse-ingest")
        buffer: dict[str, list[dict[str, Any]]] = defaultdict(list)
        last_flush = time.monotonic()
        while True:
            for tp, records in consumer.poll(timeout_ms=200).items():
                buffer[Topics.INGESTED[tp.topic]].extend(r.value for r in records)
            if time.monotonic() - last_flush >= self.flush_seconds:
                for table, rows in buffer.items():
                    try:
                        ch.insert(table, rows)
                        self.rows_ingested += len(rows)
                    except Exception:  # on garde la boucle vivante pendant la démo
                        log.exception("insert %s failed", table)
                buffer.clear()
                last_flush = time.monotonic()
