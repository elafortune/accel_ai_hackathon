"""Détection déterministe d'anomalies dans ClickHouse (fenêtres en temps simulé).

Les stratégies ne voient jamais le flux brut : elles ne reçoivent que ces alertes.
La règle de tendance ne filtre volontairement pas sur le nombre d'auteurs distincts :
juger si un pic est réel ou artificiel est le travail de la stratégie (c'est ce que teste
le scénario « fausse tendance »).
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

from app import bus
from app.config import Topics
from app.simulator import REALTIME_WORLDS
from app.stores import ch

log = logging.getLogger("detector")

TREND_SPIKE_SQL = """
WITH (SELECT max(sim_ts) FROM social) AS now
SELECT matched_sku AS sku,
       countIf(similarity >= 0.8 AND sim_ts > now - INTERVAL 30 MINUTE) AS recent_posts,
       uniqExactIf(author, similarity >= 0.8 AND sim_ts > now - INTERVAL 30 MINUTE) AS recent_authors,
       countIf(similarity >= 0.8 AND sim_ts <= now - INTERVAL 30 MINUTE AND sim_ts > now - INTERVAL 150 MINUTE) / 4 AS baseline_per_30min,
       round(avgIf(similarity, similarity >= 0.8 AND sim_ts > now - INTERVAL 30 MINUTE), 3) AS avg_similarity
FROM social
WHERE sim_ts > now - INTERVAL 150 MINUTE
GROUP BY sku
HAVING recent_posts >= 8 AND recent_posts > 3 * (baseline_per_30min + 1)
"""

BURN_WITHOUT_STOCK_SQL = """
WITH (SELECT max(sim_ts) FROM inventory WHERE world = '{world}') AS now
SELECT i.sku AS sku, i.out_sizes AS out_sizes, a.spend_last_hour AS spend_last_hour
FROM (
    SELECT sku, groupArrayIf(size, stock <= 0) AS out_sizes
    FROM inventory WHERE world = '{world}' AND sim_ts = now GROUP BY sku
) AS i
INNER JOIN (
    SELECT sku, sum(spend) AS spend_last_hour, argMax(daily_budget, sim_ts) AS budget
    FROM ads WHERE world = '{world}' AND sim_ts > now - INTERVAL 60 MINUTE GROUP BY sku
) AS a USING sku
WHERE has(i.out_sizes, 'M') AND has(i.out_sizes, 'L') AND a.budget > 0
"""

SELLOUT_RISK_SQL = """
WITH (SELECT max(sim_ts) FROM inventory WHERE world = '{world}') AS now
SELECT s.sku AS sku, s.stock AS stock, o.sold_2h AS sold_2h,
       round(s.stock / (o.sold_2h / 2), 1) AS hours_left
FROM (
    SELECT sku, sum(stock) AS stock FROM inventory
    WHERE world = '{world}' AND sim_ts = now GROUP BY sku
) AS s
INNER JOIN (
    SELECT sku, sum(qty) AS sold_2h FROM orders
    WHERE world = '{world}' AND sim_ts > now - INTERVAL 120 MINUTE GROUP BY sku
) AS o USING sku
WHERE o.sold_2h >= 4 AND s.stock > 0 AND s.stock / (o.sold_2h / 2) < 8
"""

RULES = {
    "trend_spike": TREND_SPIKE_SQL,
    "burn_without_stock": BURN_WITHOUT_STOCK_SQL,
    "sellout_risk": SELLOUT_RISK_SQL,
}
# Délai avant de ré-alerter sur un même (monde, type, modèle), en minutes simulées
COOLDOWN_MINUTES = {"trend_spike": 180, "burn_without_stock": 60, "sellout_risk": 180}


class AlertGate:
    """Anti-répétition des alertes, sur une horloge fournie (temps simulé)."""

    def __init__(self, clock_minutes: Callable[[], float]) -> None:
        self.clock = clock_minutes
        self.last: dict[tuple[str, str, str], float] = {}

    def allow(self, world: str, alert_type: str, sku: str) -> bool:
        key, now = (world, alert_type, sku), self.clock()
        if now - self.last.get(key, -1e9) < COOLDOWN_MINUTES[alert_type]:
            return False
        self.last[key] = now
        return True


def scan(world: str, gate: AlertGate) -> list[dict[str, Any]]:
    alerts = []
    for alert_type, sql in RULES.items():
        for row in ch.query(sql.format(world=world)):
            if gate.allow(world, alert_type, row["sku"]):
                alerts.append({"type": alert_type, "world": world, "sku": row["sku"], "evidence": row,
                               "detected_at": time.time()})
    return alerts


class Detector(threading.Thread):
    """Mode live : scanne ClickHouse en continu et publie les alertes sur Kafka."""

    def __init__(self, clock_minutes: Callable[[], float], interval: float = 2.0) -> None:
        super().__init__(daemon=True, name="detector")
        self.interval = interval
        self.gate = AlertGate(clock_minutes)
        self.producer = bus.producer()

    def run(self) -> None:
        while True:
            for world in REALTIME_WORLDS:
                try:
                    for alert in scan(world, self.gate):
                        self.producer.send(Topics.ALERTS, alert)
                except Exception:
                    log.exception("scan %s failed", world)
            time.sleep(self.interval)
