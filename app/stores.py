"""Clients ClickHouse (HTTP) et PostgreSQL (pg8000), sans dépendance native."""
from __future__ import annotations

import json
import ssl
import threading
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import httpx
import pg8000.native

from app.config import settings


class ClickHouse:
    def __init__(self) -> None:
        self._client = httpx.Client(
            base_url=settings.clickhouse_url,
            auth=(settings.clickhouse_user, settings.clickhouse_password),
            timeout=30,
        )

    def command(self, sql: str) -> None:
        r = self._client.post("/", content=sql.encode())
        if r.status_code != 200:
            raise RuntimeError(f"ClickHouse: {r.text[:500]}")

    def query(self, sql: str) -> list[dict[str, Any]]:
        r = self._client.post("/", content=f"{sql.rstrip().rstrip(';')} FORMAT JSON".encode())
        if r.status_code != 200:
            raise RuntimeError(f"ClickHouse: {r.text[:500]}")
        return r.json()["data"]

    def insert(self, table: str, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        body = "\n".join(json.dumps(row, default=str) for row in rows)
        r = self._client.post(
            "/",
            params={"query": f"INSERT INTO {table} FORMAT JSONEachRow",
                    "input_format_skip_unknown_fields": 1},
            content=body.encode(),
        )
        if r.status_code != 200:
            raise RuntimeError(f"ClickHouse insert {table}: {r.text[:500]}")


class Postgres:
    """Connexion unique protégée par un verrou : suffisant pour la démo mono-process."""

    def __init__(self) -> None:
        u = urlparse(settings.pg_url)
        params = parse_qs(u.query)
        ssl_context = None
        if params.get("sslmode", ["disable"])[0] in ("require", "verify-ca", "verify-full"):
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        self._conn = pg8000.native.Connection(
            user=unquote(u.username or ""),
            password=unquote(u.password or ""),
            host=u.hostname or "localhost",
            port=u.port or 5432,
            database=u.path.lstrip("/") or "postgres",
            ssl_context=ssl_context,
        )
        self._lock = threading.Lock()

    def run(self, sql: str, **params: Any) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.run(sql, **params)
            cols = [c["name"] for c in (self._conn.columns or [])]
        return [dict(zip(cols, r)) for r in rows or []]


ch = ClickHouse()
_pg: Postgres | None = None


def pg() -> Postgres:
    global _pg
    if _pg is None:
        _pg = Postgres()
    return _pg
