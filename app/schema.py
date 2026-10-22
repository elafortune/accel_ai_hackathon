"""Création des tables ClickHouse / PostgreSQL et chargement du catalogue."""
from __future__ import annotations

import json

from app.catalog import CATALOG
from app.stores import ch, pg

CLICKHOUSE_DDL = [
    """CREATE TABLE IF NOT EXISTS orders (
        sim_ts DateTime, world LowCardinality(String), sku String, size LowCardinality(String),
        qty UInt16, revenue Float32, margin Float32
    ) ENGINE = MergeTree ORDER BY (world, sku, sim_ts)""",
    """CREATE TABLE IF NOT EXISTS ads (
        sim_ts DateTime, world LowCardinality(String), sku String, daily_budget Float32,
        spend Float32, clicks UInt32, in_stock UInt8
    ) ENGINE = MergeTree ORDER BY (world, sku, sim_ts)""",
    """CREATE TABLE IF NOT EXISTS inventory (
        sim_ts DateTime, world LowCardinality(String), sku String, size LowCardinality(String), stock Int32
    ) ENGINE = MergeTree ORDER BY (world, sku, size, sim_ts)""",
    """CREATE TABLE IF NOT EXISTS social (
        sim_ts DateTime, post_id String, author String, matched_sku String,
        similarity Float32, similarity_source LowCardinality(String)
    ) ENGINE = MergeTree ORDER BY (matched_sku, sim_ts)""",
    """CREATE TABLE IF NOT EXISTS lost_sales (
        sim_ts DateTime, world LowCardinality(String), sku String, size LowCardinality(String), qty UInt16
    ) ENGINE = MergeTree ORDER BY (world, sku, sim_ts)""",
]

POSTGRES_DDL = [
    """CREATE TABLE IF NOT EXISTS catalog (
        sku TEXT PRIMARY KEY, name TEXT, category TEXT, color TEXT,
        price NUMERIC, unit_cost NUMERIC, margin_pct NUMERIC, reorder_lead_time_hours INT
    )""",
    """CREATE TABLE IF NOT EXISTS agent_trace (
        id BIGSERIAL PRIMARY KEY, ts TIMESTAMPTZ DEFAULT now(), run_id TEXT, agent TEXT,
        sku TEXT, kind TEXT, content TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS reorders (
        id BIGSERIAL PRIMARY KEY, sku TEXT, size TEXT, qty INT, ordered_sim_ts TIMESTAMP, arrival_sim_ts TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS decisions (
        id BIGSERIAL PRIMARY KEY, ts TIMESTAMPTZ DEFAULT now(), run_id TEXT, agent TEXT,
        alert_type TEXT, sku TEXT, summary TEXT, actions JSONB
    )""",
]


def reset_all() -> None:
    for table in ("orders", "ads", "inventory", "social", "lost_sales"):
        ch.command(f"DROP TABLE IF EXISTS {table}")
    for ddl in CLICKHOUSE_DDL:
        ch.command(ddl)

    db = pg()
    for table in ("agent_trace", "decisions", "reorders", "catalog"):
        db.run(f"DROP TABLE IF EXISTS {table}")
    for ddl in POSTGRES_DDL:
        db.run(ddl)
    for p in CATALOG:
        db.run(
            "INSERT INTO catalog VALUES (:sku, :name, :category, :color, :price, :cost, :margin, :lead)",
            sku=p.sku, name=p.name, category=p.category, color=p.color,
            price=p.price, cost=p.unit_cost, margin=p.margin_pct, lead=3,
        )


if __name__ == "__main__":
    reset_all()
    print(json.dumps({"catalog": len(CATALOG), "status": "ok"}))
