"""Outils de l'agent : lecture (ClickHouse / Postgres) et actions (via Kafka), avec garde-fous."""
from __future__ import annotations

import json
from typing import Any, Callable

from app import bus
from app.catalog import BY_SKU, CATALOG, SIZE_MIX, SIZES
from app.simulator import REORDER_LEAD_HOURS
from app.config import Topics
from app.stores import ch, pg

WORLD = "agent"
MAX_BUDGET_MULTIPLIER = 3.0          # un budget ne peut pas dépasser 3x sa valeur initiale
TOTAL_BUDGET_CAP = 1.3 * sum(p.base_daily_budget for p in CATALOG)

_producer = None
_sink: Callable[[dict[str, Any]], Any] | None = None   # remplacé par le benchmark (application directe)


def set_action_sink(sink: Callable[[dict[str, Any]], Any] | None) -> None:
    global _sink
    _sink = sink


def _send_action(action: dict[str, Any]) -> None:
    global _producer
    action = {**action, "world": WORLD}
    if _sink is not None:
        _sink(action)
        return
    if _producer is None:
        _producer = bus.producer()
    _producer.send(Topics.ACTIONS, action)
    _producer.flush()


def _check_sku(sku: str) -> None:
    if sku not in BY_SKU:
        raise ValueError(f"modèle inconnu : {sku}")


def _sim_now() -> str:
    return ch.query("SELECT toString(max(sim_ts)) AS now FROM inventory")[0]["now"]


def _pending_reorders(sku: str) -> dict[str, int]:
    rows = pg().run("SELECT size, sum(qty) AS qty FROM reorders WHERE sku = :sku AND arrival_sim_ts > "
                    "CAST(:now AS TIMESTAMP) GROUP BY size", sku=sku, now=_sim_now())
    return {r["size"]: int(r["qty"]) for r in rows}


def _current_budgets() -> dict[str, float]:
    rows = ch.query(f"""
        SELECT sku, argMax(daily_budget, sim_ts) AS budget FROM ads
        WHERE world = '{WORLD}' AND sim_ts > (SELECT max(sim_ts) FROM ads) - INTERVAL 30 MINUTE
        GROUP BY sku""")
    return {r["sku"]: float(r["budget"]) for r in rows}


# ------------------------------------------------------------------ lecture
def get_sku_snapshot(sku: str) -> dict[str, Any]:
    _check_sku(sku)
    meta = pg().run("SELECT name, category, price, unit_cost, margin_pct FROM catalog WHERE sku = :sku", sku=sku)[0]
    stock = ch.query(f"""
        SELECT size, argMax(stock, sim_ts) AS stock FROM inventory
        WHERE world = '{WORLD}' AND sku = '{sku}' GROUP BY size ORDER BY size""")
    sales = ch.query(f"""
        WITH (SELECT max(sim_ts) FROM orders) AS now
        SELECT sumIf(qty, sim_ts > now - INTERVAL 1 HOUR) AS units_1h,
               sumIf(qty, sim_ts > now - INTERVAL 6 HOUR) AS units_6h
        FROM orders WHERE world = '{WORLD}' AND sku = '{sku}'""")[0]
    ads = ch.query(f"""
        WITH (SELECT max(sim_ts) FROM ads) AS now
        SELECT argMax(daily_budget, sim_ts) AS daily_budget,
               round(sumIf(spend, sim_ts > now - INTERVAL 1 HOUR), 2) AS spend_1h,
               sumIf(clicks, sim_ts > now - INTERVAL 1 HOUR) AS clicks_1h
        FROM ads WHERE world = '{WORLD}' AND sku = '{sku}'""")[0]
    return {
        "sku": sku, "name": meta["name"], "category": meta["category"],
        "price": float(meta["price"]), "unit_cost": float(meta["unit_cost"]), "margin_pct": float(meta["margin_pct"]),
        "stock_by_size": {r["size"]: int(r["stock"]) for r in stock},
        "units_sold_last_1h": int(sales["units_1h"]), "units_sold_last_6h": int(sales["units_6h"]),
        "ads": {"daily_budget": float(ads["daily_budget"]), "spend_last_1h": float(ads["spend_1h"]),
                "clicks_last_1h": int(ads["clicks_1h"])},
        "pending_reorders_by_size": _pending_reorders(sku),
        "reorder_lead_time_hours": REORDER_LEAD_HOURS,
    }


def get_trend_signal(sku: str) -> dict[str, Any]:
    _check_sku(sku)
    rows = ch.query(f"""
        WITH (SELECT max(sim_ts) FROM social) AS now
        SELECT toStartOfInterval(sim_ts, INTERVAL 30 MINUTE) AS window,
               countIf(similarity >= 0.8) AS similar_posts,
               uniqExactIf(author, similarity >= 0.8) AS distinct_authors,
               round(avgIf(similarity, similarity >= 0.8), 3) AS avg_similarity
        FROM social WHERE matched_sku = '{sku}' AND sim_ts > now - INTERVAL 3 HOUR
        GROUP BY window ORDER BY window""")
    source = ch.query("SELECT any(similarity_source) AS s FROM social")[0]["s"]
    return {"sku": sku, "windows_30min": rows, "similarity_source": source}


def forecast_sellout(sku: str) -> dict[str, Any]:
    snap = get_sku_snapshot(sku)
    rows = ch.query(f"""
        WITH (SELECT max(sim_ts) FROM orders) AS now
        SELECT size, sum(qty) AS sold_2h FROM orders
        WHERE world = '{WORLD}' AND sku = '{sku}' AND sim_ts > now - INTERVAL 2 HOUR GROUP BY size""")
    rate = {r["size"]: int(r["sold_2h"]) / 2 for r in rows}
    hours_left = {
        s: (round(snap["stock_by_size"].get(s, 0) / rate[s], 1) if rate.get(s) else None) for s in SIZES
    }
    pending = snap["pending_reorders_by_size"]
    # Rythme total (robuste) réparti selon la courbe de tailles de la marque, plutôt que par taille (trop bruité)
    total_rate = sum(rate.values())
    demand_24h = {s: round(total_rate * 24 * SIZE_MIX[s]) for s in SIZES}
    # Quantité pour couvrir 24 h de demande au rythme actuel, moins le stock et les réassorts déjà en route
    suggested = {s: max(0, demand_24h[s] - snap["stock_by_size"].get(s, 0) - pending.get(s, 0)) for s in SIZES}
    return {"sku": sku, "units_per_hour_by_size": rate, "hours_before_stockout_by_size": hours_left,
            "stock_by_size": snap["stock_by_size"], "pending_reorders_by_size": pending,
            "expected_demand_next_24h_by_size": demand_24h, "suggested_reorder_qty_by_size": suggested,
            "unit_margin": round(snap["price"] - snap["unit_cost"], 2),
            "reorder_premium_per_unit": round(snap["unit_cost"] * 0.15, 2)}


def find_substitutes(sku: str) -> list[dict[str, Any]]:
    _check_sku(sku)
    category = BY_SKU[sku].category
    candidates = [p for p in CATALOG if p.category == category and p.sku != sku]
    result = []
    for p in candidates:
        snap = get_sku_snapshot(p.sku)
        result.append({"sku": p.sku, "name": p.name, "color": p.color, "margin_pct": p.margin_pct,
                       "total_stock": sum(snap["stock_by_size"].values()),
                       "stock_by_size": snap["stock_by_size"], "daily_budget": snap["ads"]["daily_budget"]})
    return result


# ------------------------------------------------------------------ actions
def set_ad_budget(sku: str, daily_budget: float, reason: str) -> dict[str, Any]:
    _check_sku(sku)
    cap = BY_SKU[sku].base_daily_budget * MAX_BUDGET_MULTIPLIER
    if daily_budget > cap:
        return {"status": "refusé", "reason": f"garde-fou : budget max {cap:.0f} €/jour pour ce modèle"}
    budgets = _current_budgets()
    total_after = sum(budgets.values()) - budgets.get(sku, 0) + daily_budget
    if total_after > TOTAL_BUDGET_CAP:
        return {"status": "refusé",
                "reason": f"garde-fou : budget total {total_after:.0f} € > plafond {TOTAL_BUDGET_CAP:.0f} €. "
                          "Réduire d'abord un autre modèle."}
    _send_action({"type": "set_ad_budget", "sku": sku, "daily_budget": round(daily_budget, 2), "reason": reason})
    return {"status": "appliqué", "sku": sku, "daily_budget": round(daily_budget, 2),
            "previous_budget": budgets.get(sku)}


def feature_product(sku: str, reason: str) -> dict[str, Any]:
    _check_sku(sku)
    _send_action({"type": "feature", "sku": sku, "reason": reason})
    return {"status": "appliqué", "sku": sku, "note": "mis en avant en page d'accueil (3 emplacements max)"}


def create_reorder(sku: str, size: str, qty: int, reason: str) -> dict[str, Any]:
    _check_sku(sku)
    if size not in SIZES or not 1 <= qty <= 200:
        return {"status": "refusé", "reason": "taille inconnue ou quantité hors bornes (1-200)"}
    _send_action({"type": "reorder", "sku": sku, "size": size, "qty": qty, "reason": reason})
    now = _sim_now()
    pg().run("INSERT INTO reorders (sku, size, qty, ordered_sim_ts, arrival_sim_ts) VALUES "
             "(:sku, :size, :qty, CAST(:now AS TIMESTAMP), CAST(:now AS TIMESTAMP) + make_interval(hours => :h))",
             sku=sku, size=size, qty=qty, now=now, h=REORDER_LEAD_HOURS)
    return {"status": "appliqué", "sku": sku, "size": size, "qty": qty, "arrival_in_hours": REORDER_LEAD_HOURS}


TOOLS: dict[str, Callable[..., Any]] = {
    "get_sku_snapshot": get_sku_snapshot,
    "get_trend_signal": get_trend_signal,
    "forecast_sellout": forecast_sellout,
    "find_substitutes": find_substitutes,
    "set_ad_budget": set_ad_budget,
    "feature_product": feature_product,
    "create_reorder": create_reorder,
}


def _fn(name: str, description: str, props: dict[str, Any]) -> dict[str, Any]:
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": props, "required": list(props),
                       "additionalProperties": False}}}


_SKU = {"type": "string", "description": "Identifiant du modèle, ex. SKU-0712"}
_REASON = {"type": "string", "description": "Justification courte, affichée au responsable e-commerce"}

TOOL_SCHEMAS = [
    _fn("get_sku_snapshot", "Stock par taille, ventes récentes, marge et pub en cours d'un modèle.", {"sku": _SKU}),
    _fn("get_trend_signal", "Publications sociales visuellement similaires au modèle, par fenêtre de 30 min "
        "(nombre, auteurs distincts, similarité moyenne).", {"sku": _SKU}),
    _fn("forecast_sellout", "Prévision par taille au rythme des 2 dernières heures : heures avant rupture, demande "
        "attendue sur 24 h, réassorts déjà en route et quantité de réassort suggérée.", {"sku": _SKU}),
    _fn("find_substitutes", "Modèles de la même catégorie avec leur stock, marge et budget pub.", {"sku": _SKU}),
    _fn("set_ad_budget", "Fixe le budget pub quotidien (€) d'un modèle. 0 = pause. Rendements décroissants : "
        "au-delà du budget initial le coût par clic augmente, une hausse n'est rentable que si la conversion monte "
        "(vraie tendance). Garde-fous : 3x le budget initial max par modèle, budget total plafonné.",
        {"sku": _SKU, "daily_budget": {"type": "number"}, "reason": _REASON}),
    _fn("feature_product", "Met le modèle en avant en page d'accueil (augmente la conversion).",
        {"sku": _SKU, "reason": _REASON}),
    _fn("create_reorder", "Commande un réassort express (arrivée sous 3 h) pour une taille. Surcoût de 15 % du "
        "coût unitaire par pièce commandée, même si elle ne se vend pas.",
        {"sku": _SKU, "size": {"type": "string", "enum": SIZES}, "qty": {"type": "integer"}, "reason": _REASON}),
]


def call_tool(name: str, arguments: str | dict[str, Any]) -> str:
    args = json.loads(arguments) if isinstance(arguments, str) else arguments
    try:
        return json.dumps(TOOLS[name](**args), default=str, ensure_ascii=False)
    except Exception as exc:  # renvoyé à l'agent comme observation d'erreur
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
