"""Stratégie « règles temps réel sans LLM » : mêmes alertes que l'agent, réponses fixes.

Sert à séparer la valeur du temps réel (que ces règles captent) de la valeur du raisonnement
de l'agent (enquête, arbitrage, refus d'agir sur un signal douteux).
"""
from __future__ import annotations

from typing import Any

from app.catalog import BY_SKU, SIZES
from app.simulator import Simulator

WORLD = "realtime_rules"


def realtime_rules(alert: dict[str, Any], sim: Simulator) -> list[dict[str, Any]]:
    sku = alert["sku"]
    w = sim.worlds[WORLD]
    actions: list[dict[str, Any]] = []
    if alert["type"] == "burn_without_stock":
        actions.append({"type": "set_ad_budget", "sku": sku, "daily_budget": 0})
    elif alert["type"] == "trend_spike":
        cap = BY_SKU[sku].base_daily_budget * 3
        actions.append({"type": "set_ad_budget", "sku": sku, "daily_budget": min(cap, w.budget[sku] * 2)})
        actions.append({"type": "feature", "sku": sku})
    elif alert["type"] == "sellout_risk":
        actions += [{"type": "reorder", "sku": sku, "size": s, "qty": 20} for s in SIZES]
    for a in actions:
        sim.apply_action({**a, "world": WORLD})
    return actions
