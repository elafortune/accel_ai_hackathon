"""Simulateur en boucle fermée : deux mondes identiques (même seed) qui divergent par leurs décisions.

- monde "baseline" : règles appliquées une fois par jour sur les données de la veille
  (ce que fait une bonne équipe e-commerce aujourd'hui) ;
- monde "realtime_rules" : règles fixes déclenchées par les mêmes alertes temps réel (sans LLM) ;
- monde "agent"    : piloté en temps réel par nos agents via le topic actions.commands.

La vérité terrain (tendances virales, ruptures) est commune aux deux mondes. Les actions
modifient réellement les ventes et les clics : les gains affichés ne sont pas fictifs.
"""
from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from app import bus
from app.catalog import BY_SKU, CATALOG, SIZE_MIX, SIZES
from app.config import Topics, settings
from app.similarity import SOURCE as SIMILARITY_SOURCE, match_post

CPC = 0.70                 # coût par clic moyen (€)
BASE_CVR = 0.018           # taux de conversion d'un clic payant
FEATURE_BOOST = 1.4        # effet d'une mise en avant en page d'accueil
VIRAL_PEAK = 12.0          # multiplicateur de demande au pic d'une vague virale
REORDER_LEAD_HOURS = 3     # réassort express
REORDER_PREMIUM = 0.15     # surcoût du réassort express (part du coût unitaire)
CPC_ELASTICITY = 0.5       # rendements décroissants : CPC x (budget / budget initial)^0.5 au-delà du budget initial
SIM_START = datetime(2026, 10, 22, 9, 0)
STRATEGIES = ["baseline_j1", "realtime_rules", "agent"]
REALTIME_WORLDS = ["realtime_rules", "agent"]


def poisson(rng: random.Random, lam: float) -> int:
    if lam <= 0:
        return 0
    if lam > 30:
        return max(0, round(rng.gauss(lam, math.sqrt(lam))))
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def hour_factor(ts: datetime) -> float:
    h = ts.hour
    if h < 7:
        return 0.25
    if 19 <= h <= 22:
        return 1.5
    return 1.0


@dataclass
class World:
    name: str
    rng: random.Random
    stock: dict[str, dict[str, int]] = field(default_factory=dict)
    budget: dict[str, float] = field(default_factory=dict)
    featured: set[str] = field(default_factory=set)
    reorders: list[tuple[int, str, str, int]] = field(default_factory=list)
    kpi: dict[str, float] = field(default_factory=lambda: {
        "revenue": 0.0, "gross_margin": 0.0, "ad_spend": 0.0, "wasted_ad_spend": 0.0,
        "units": 0, "lost_units": 0, "lost_margin": 0.0, "reorder_units": 0, "reorder_premium": 0.0,
    })
    spend_by_sku: dict[str, float] = field(default_factory=dict)
    units_by_sku: dict[str, int] = field(default_factory=dict)
    sales_today: dict[str, int] = field(default_factory=dict)
    sales_yesterday: dict[str, int] = field(default_factory=dict)
    actions_log: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def create(cls, name: str, seed: int) -> "World":
        w = cls(name=name, rng=random.Random(seed))
        for p in CATALOG:
            w.stock[p.sku] = dict(p.initial_stock)
            w.budget[p.sku] = p.base_daily_budget
        return w

    @property
    def profit(self) -> float:
        return self.kpi["gross_margin"] - self.kpi["ad_spend"] - self.kpi["reorder_premium"]


class Simulator(threading.Thread):
    def __init__(self, seed: int = 42, worlds: list[str] | None = None, publish: bool = True) -> None:
        super().__init__(daemon=True, name="simulator")
        self.minutes = settings.sim_minutes_per_tick
        self.ticks_per_day = 1440 // self.minutes
        self.tick = 0
        self.worlds = {n: World.create(n, seed) for n in (worlds or STRATEGIES)}
        self.social_rng = random.Random(seed + 1)
        self.virals: list[dict[str, Any]] = []
        self.fake_trends: list[dict[str, Any]] = []
        self.trend: dict[str, float] = {p.sku: 1.0 for p in CATALOG}
        self.lock = threading.Lock()
        self.producer = bus.producer() if publish else None
        self.running = True

    # ------------------------------------------------------------------ temps
    @property
    def now(self) -> datetime:
        return SIM_START + timedelta(minutes=self.tick * self.minutes)

    def hours_to_ticks(self, hours: float) -> int:
        return max(1, round(hours * 60 / self.minutes))

    # ------------------------------------------------------------ scénarios
    def inject(self, scenario: dict[str, Any]) -> None:
        with self.lock:
            kind = scenario.get("type")
            if kind == "viral":
                sku = scenario.get("sku") or "SKU-0712"
                self.virals.append({"sku": sku, "start": self.tick})
            elif kind == "fake_trend":
                # Pic de posts très similaires venant d'une poignée de comptes (robots) : aucune demande réelle
                self.fake_trends.append({"sku": scenario.get("sku") or "SKU-2230", "start": self.tick})
            elif kind == "stockout":
                sku = scenario.get("sku") or "SKU-1104"
                for w in self.worlds.values():
                    for size in ("M", "L"):
                        w.stock[sku][size] = 0

    def _update_trends(self) -> None:
        for sku in self.trend:
            self.trend[sku] = 1.0
        for v in self.virals:
            age = self.tick - v["start"]
            lag = 2
            if age < lag:
                continue
            ramp = min(1.0, (age - lag) / self.hours_to_ticks(2))
            decay = math.exp(-(age - lag) / self.hours_to_ticks(24))
            self.trend[v["sku"]] = max(self.trend[v["sku"]], 1 + (VIRAL_PEAK - 1) * ramp * decay)

    def _social_posts(self, ts: datetime) -> list[dict[str, Any]]:
        rng = self.social_rng
        truths: list[str | None] = [None] * poisson(rng, 3)
        if rng.random() < 0.05:  # bruit : un post isolé ressemblant fortement à un modèle
            truths.append(rng.choice(CATALOG).sku)
        for v in self.virals:
            age = self.tick - v["start"]
            if 0 <= age < self.hours_to_ticks(24):
                truths += [v["sku"]] * poisson(rng, 2 + 12 * min(1.0, age / 6) * math.exp(-age / self.hours_to_ticks(12)))
        bots: list[str] = []
        for f in self.fake_trends:
            age = self.tick - f["start"]
            if 0 <= age < self.hours_to_ticks(6):
                bots += [f["sku"]] * poisson(rng, 10)
        posts = []
        for truth in bots:
            posts.append({
                "sim_ts": ts, "post_id": uuid.uuid4().hex[:12], "author": f"promo_bot_{rng.randint(1, 3)}",
                "matched_sku": truth, "similarity": match_post(truth, rng)[1], "similarity_source": SIMILARITY_SOURCE,
            })
        for truth in truths:
            sku, score = match_post(truth, rng)
            posts.append({
                "sim_ts": ts, "post_id": uuid.uuid4().hex[:12],
                "author": f"user_{rng.randint(1, 5000) if truth else rng.randint(1, 300)}",
                "matched_sku": sku, "similarity": score, "similarity_source": SIMILARITY_SOURCE,
            })
        return posts

    # ------------------------------------------------------------- actions
    def apply_action(self, action: dict[str, Any]) -> str:
        """Applique une action au monde indiqué (par défaut 'agent'). Retourne un message d'état."""
        with self.lock:
            w = self.worlds.get(action.get("world", "agent"))
            if w is None:
                return "monde inconnu"
            sku = action.get("sku", "")
            if sku not in BY_SKU:
                return f"modèle inconnu {sku}"
            kind = action["type"]
            if kind == "set_ad_budget":
                w.budget[sku] = max(0.0, float(action["daily_budget"]))
            elif kind == "feature":
                if len(w.featured) >= 3 and sku not in w.featured:
                    w.featured.pop()
                w.featured.add(sku)
            elif kind == "unfeature":
                w.featured.discard(sku)
            elif kind == "reorder":
                self._schedule_reorder(w, sku, action["size"], int(action["qty"]))
            else:
                return f"action inconnue {kind}"
            w.actions_log.append({"tick": self.tick, **action})
            return "ok"

    def _schedule_reorder(self, w: World, sku: str, size: str, qty: int) -> None:
        w.reorders.append((self.tick + self.hours_to_ticks(REORDER_LEAD_HOURS), sku, size, qty))
        w.kpi["reorder_units"] += qty
        w.kpi["reorder_premium"] += qty * BY_SKU[sku].unit_cost * REORDER_PREMIUM

    def _baseline_daily_rules(self, w: World) -> None:
        """Règles quotidiennes sur les données de la veille (comparaison de référence)."""
        top = sorted(w.sales_yesterday.items(), key=lambda kv: kv[1], reverse=True)[:3]
        for p in CATALOG:
            total = sum(w.stock[p.sku].values())
            if total == 0:
                w.budget[p.sku] = 0.0
            elif w.budget[p.sku] == 0.0:
                w.budget[p.sku] = p.base_daily_budget
            sold = w.sales_yesterday.get(p.sku, 0)
            if total < 2 * sold:
                for size in SIZES:
                    self._schedule_reorder(w, p.sku, size, max(5, round(sold * SIZE_MIX[size] * 3)))
        for sku, _ in top:
            if sum(w.stock[sku].values()) > 0:
                w.budget[sku] = round(w.budget[sku] * 1.2, 2)

    # ------------------------------------------------------------ boucle
    def step(self) -> dict[str, list[dict[str, Any]]]:
        with self.lock:
            ts = self.now
            self._update_trends()
            out: dict[str, list[dict[str, Any]]] = {t: [] for t in Topics.INGESTED}
            out[Topics.SOCIAL] = self._social_posts(ts)

            new_day = self.tick > 0 and self.tick % self.ticks_per_day == 0
            for w in self.worlds.values():
                if new_day:
                    w.sales_yesterday, w.sales_today = w.sales_today, {}
                    if w.name == "baseline_j1":
                        self._baseline_daily_rules(w)
                self._step_world(w, ts, out)
            self.tick += 1

        if self.producer is not None:
            for topic, rows in out.items():
                for row in rows:
                    self.producer.send(topic, row)
        return out

    def _step_world(self, w: World, ts: datetime, out: dict[str, list[dict[str, Any]]]) -> None:
        arrived = [r for r in w.reorders if r[0] <= self.tick]
        w.reorders = [r for r in w.reorders if r[0] > self.tick]
        for _, sku, size, qty in arrived:
            w.stock[sku][size] += qty

        hf = hour_factor(ts)
        for p in CATALOG:
            m = self.trend[p.sku]
            boost = FEATURE_BOOST if p.sku in w.featured else 1.0
            organic = p.base_daily_demand / self.ticks_per_day * hf * m * boost
            cpc = CPC * max(1.0, w.budget[p.sku] / p.base_daily_budget) ** CPC_ELASTICITY
            clicks = poisson(w.rng, w.budget[p.sku] / self.ticks_per_day / cpc * hf)
            spend = clicks * cpc
            paid = sum(1 for _ in range(clicks) if w.rng.random() < BASE_CVR * m * boost)
            demand = poisson(w.rng, organic) + paid

            sold: dict[str, int] = {}
            lost: dict[str, int] = {}
            for _ in range(demand):
                size = w.rng.choices(SIZES, weights=[SIZE_MIX[s] for s in SIZES])[0]
                if w.stock[p.sku][size] > 0:
                    w.stock[p.sku][size] -= 1
                    sold[size] = sold.get(size, 0) + 1
                else:
                    lost[size] = lost.get(size, 0) + 1

            unavailable_share = sum(SIZE_MIX[s] for s in SIZES if w.stock[p.sku][s] == 0)
            units = sum(sold.values())
            w.kpi["revenue"] += units * p.price
            w.kpi["gross_margin"] += units * (p.price - p.unit_cost)
            w.kpi["units"] += units
            w.kpi["ad_spend"] += spend
            w.kpi["wasted_ad_spend"] += spend * unavailable_share
            w.kpi["lost_units"] += sum(lost.values())
            w.kpi["lost_margin"] += sum(lost.values()) * (p.price - p.unit_cost)
            w.sales_today[p.sku] = w.sales_today.get(p.sku, 0) + units
            w.spend_by_sku[p.sku] = w.spend_by_sku.get(p.sku, 0.0) + spend
            w.units_by_sku[p.sku] = w.units_by_sku.get(p.sku, 0) + units

            for size, qty in sold.items():
                out[Topics.ORDERS].append({"sim_ts": ts, "world": w.name, "sku": p.sku, "size": size, "qty": qty,
                                           "revenue": qty * p.price, "margin": qty * (p.price - p.unit_cost)})
            for size, qty in lost.items():
                out[Topics.LOST_SALES].append({"sim_ts": ts, "world": w.name, "sku": p.sku, "size": size, "qty": qty})
            out[Topics.ADS].append({"sim_ts": ts, "world": w.name, "sku": p.sku, "daily_budget": w.budget[p.sku],
                                    "spend": spend, "clicks": clicks,
                                    "in_stock": int(sum(w.stock[p.sku].values()) > 0)})
            for size in SIZES:
                out[Topics.INVENTORY].append({"sim_ts": ts, "world": w.name, "sku": p.sku, "size": size,
                                              "stock": w.stock[p.sku][size]})

    def run(self) -> None:
        while self.running:
            started = time.monotonic()
            self.step()
            time.sleep(max(0.0, settings.tick_seconds - (time.monotonic() - started)))

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "sim_time": self.now.isoformat(),
                "tick": self.tick,
                "worlds": {n: {**{k: round(v, 2) for k, v in w.kpi.items()}, "profit": round(w.profit, 2),
                               "featured": sorted(w.featured)} for n, w in self.worlds.items()},
                "trend_truth": {k: round(v, 2) for k, v in self.trend.items() if v > 1.01},
            }
