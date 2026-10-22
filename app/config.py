"""Configuration centralisée, lue depuis l'environnement (.env).

Le même code tourne en local (docker compose) et sur Aiven : seules les variables changent.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
# ENV_FILE=.env.aiven pour viser les services Aiven sans toucher au .env local
load_dotenv(ROOT / os.getenv("ENV_FILE", ".env"))

# Un SSL_CERT_FILE pointant vers un fichier absent fait échouer httpx : on l'ignore dans ce process.
if os.environ.get("SSL_CERT_FILE") and not Path(os.environ["SSL_CERT_FILE"]).exists():
    del os.environ["SSL_CERT_FILE"]


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    kafka_bootstrap: str = os.getenv("KAFKA_BOOTSTRAP", "127.0.0.1:9092")
    kafka_ssl_dir: str = os.getenv("KAFKA_SSL_DIR", "")
    kafka_sasl_username: str = os.getenv("KAFKA_SASL_USERNAME", "")
    kafka_sasl_password: str = os.getenv("KAFKA_SASL_PASSWORD", "")

    clickhouse_url: str = os.getenv("CLICKHOUSE_URL", "http://127.0.0.1:8124")
    clickhouse_user: str = os.getenv("CLICKHOUSE_USER", "default")
    clickhouse_password: str = os.getenv("CLICKHOUSE_PASSWORD", "")

    pg_url: str = os.getenv("PG_URL", "postgresql://postgres:postgres@127.0.0.1:5442/fashion")

    tick_seconds: float = float(os.getenv("TICK_SECONDS", "1.0"))
    sim_minutes_per_tick: int = int(os.getenv("SIM_MINUTES_PER_TICK", "10"))

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_api_key)


settings = Settings()


class Topics:
    ORDERS = "events.orders"
    ADS = "events.ads.metrics"
    INVENTORY = "events.inventory"
    SOCIAL = "events.social.posts"
    LOST_SALES = "events.lost_sales"
    CONTROL = "control.scenarios"
    ALERTS = "alerts.anomalies"
    ACTIONS = "actions.commands"

    # Topics ingérés tels quels dans ClickHouse : topic -> table
    INGESTED = {
        ORDERS: "orders",
        ADS: "ads",
        INVENTORY: "inventory",
        SOCIAL: "social",
        LOST_SALES: "lost_sales",
    }
    ALL = [ORDERS, ADS, INVENTORY, SOCIAL, LOST_SALES, CONTROL, ALERTS, ACTIONS]
