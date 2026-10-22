"""Agents : Sentinel (réflexes déterministes) et Strategist (boucle ReAct LLM avec outils).

Chaque étape (pensée, action, observation, décision) est écrite dans Postgres (agent_trace)
et affichée en direct sur le dashboard.
"""
from __future__ import annotations

import json
import logging
import queue
import threading
import time
import uuid
from typing import Any

from openai import OpenAI

from app import bus
from app.catalog import BY_SKU
from app.config import Topics, settings
from app.policies import realtime_rules
from app.simulator import Simulator
from app.stores import pg
from app.tools import TOOL_SCHEMAS, call_tool, find_substitutes, forecast_sellout, get_sku_snapshot, \
    get_trend_signal, set_ad_budget, feature_product, create_reorder

log = logging.getLogger("agents")

MAX_STEPS = 8

SYSTEM_PROMPT = """Tu es le Strategist d'une marque de mode en ligne de taille moyenne. Tu pilotes en temps réel \
la pub, la mise en avant sur le site et les réassorts pour maximiser le PROFIT (marge - pub), pas le chiffre d'affaires.

Tu es déclenché par une alerte détectée dans les flux temps réel. Méthode :
1. Enquête avec les outils de lecture avant d'agir : le signal est-il réel ? peut-on servir la demande \
(stock par taille, réassort) ? est-ce rentable (marge, pub) ? quels substituts ?
2. Agis avec des actions proportionnées et réversibles. Un modèle en rupture sur ses tailles principales \
ne doit pas recevoir de pub ; une tendance réelle mérite pub + mise en avant + réassort si le stock ne suit pas ; \
le budget libéré doit aller vers un substitut rentable qui a du stock.
3. Respecte les garde-fous : si une action est refusée, adapte-toi (ex. baisse un autre budget d'abord).

Économie à garder en tête (ne devine jamais un chiffre, utilise les outils) :
- Une vente manquée coûte toute la marge unitaire (environ 65-70 % du prix). Un réassort express coûte 15 % du coût unitaire par pièce (environ 5 % du prix). Sur une demande réelle, une rupture coûte donc bien plus cher qu'un réassort un peu trop large.
- Quand un modèle se vend vite, dimensionne le réassort avec `forecast_sellout` (quantité suggérée = demande 24 h - stock - réassorts en route). Ne commande pas au compte-gouttes, et ne recommande pas ce qui est déjà en route.
- Ne coupe pas la pub d'un modèle en forte demande simplement parce que le stock baisse : réassortis. Ne coupe la pub que si les tailles principales (M, L) sont à zéro sans réassort imminent.
- Une hausse de budget n'est rentable que si la demande est réelle (beaucoup d'auteurs distincts, ventes en hausse) : un pic de posts venant de quelques comptes ne justifie aucune dépense.

Avant chaque appel d'outil, écris UNE phrase de raisonnement (ta pensée). \
Termine par un résumé de décision en 2-3 phrases, en français, avec les chiffres clés."""


def trace(run_id: str, agent: str, sku: str, kind: str, content: Any) -> None:
    text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, default=str)
    pg().run("INSERT INTO agent_trace (run_id, agent, sku, kind, content) VALUES (:r, :a, :s, :k, :c)",
             r=run_id, a=agent, s=sku, k=kind, c=text[:4000])


def record_decision(run_id: str, agent: str, alert: dict[str, Any], summary: str, actions: list[Any]) -> None:
    pg().run("INSERT INTO decisions (run_id, agent, alert_type, sku, summary, actions) "
             "VALUES (:r, :a, :t, :s, :sm, CAST(:ac AS JSONB))",
             r=run_id, a=agent, t=alert["type"], s=alert["sku"], sm=summary,
             ac=json.dumps(actions, ensure_ascii=False))


class ActionExecutor(threading.Thread):
    """Applique les actions publiées sur Kafka au monde 'agent' (rôle des API Ads / site / fournisseurs)."""

    def __init__(self, sim: Simulator) -> None:
        super().__init__(daemon=True, name="executor")
        self.sim = sim

    def run(self) -> None:
        for record in bus.consumer([Topics.ACTIONS], group_id="action-executor"):
            self.sim.apply_action(record.value)


class AgentWorker(threading.Thread):
    def __init__(self, sim: Simulator, use_llm: bool = True) -> None:
        super().__init__(daemon=True, name="agents")
        self.sim = sim
        self.inbox: queue.Queue[dict[str, Any]] = queue.Queue()
        self.client = OpenAI(api_key=settings.openai_api_key) if (settings.llm_enabled and use_llm) else None
        self.reaction_times: list[float] = []

    def handle(self, alert: dict[str, Any]) -> None:
        """Traitement synchrone d'une alerte (utilisé par le benchmark)."""
        if alert.get("world") == "realtime_rules":
            realtime_rules(alert, self.sim)
            return
        if alert["type"] == "burn_without_stock":
            self.sentinel(alert)
        self.strategist(alert)

    def run(self) -> None:
        threading.Thread(target=self._listen, daemon=True, name="alerts-listener").start()
        while True:
            alert = self.inbox.get()
            try:
                self.strategist(alert)
            except Exception:
                log.exception("strategist failed on %s", alert)

    def _listen(self) -> None:
        for record in bus.consumer([Topics.ALERTS], group_id="agents"):
            alert = record.value
            if alert.get("world") == "realtime_rules":
                realtime_rules(alert, self.sim)
                continue
            if alert["type"] == "burn_without_stock":
                self.sentinel(alert)  # réflexe immédiat, sans LLM, hors file d'attente
            self.inbox.put(alert)

    # ---------------------------------------------------------------- Sentinel
    def sentinel(self, alert: dict[str, Any]) -> None:
        run_id = uuid.uuid4().hex[:8]
        sku = alert["sku"]
        result = set_ad_budget(sku, 0, "Sentinel : tailles M et L épuisées, la pub brûle du budget")
        latency = time.time() - alert["detected_at"]
        self.reaction_times.append(latency)
        trace(run_id, "Sentinel", sku, "action",
              f"Pause pub {sku} ({BY_SKU[sku].name}) : M et L épuisées, "
              f"{alert['evidence'].get('spend_last_hour', 0):.0f} € dépensés la dernière heure. "
              f"Réaction en {latency:.1f} s.")
        record_decision(run_id, "Sentinel", alert, "Pause pub (rupture M/L)", [result])

    # -------------------------------------------------------------- Strategist
    def strategist(self, alert: dict[str, Any]) -> None:
        run_id = uuid.uuid4().hex[:8]
        sku = alert["sku"]
        trace(run_id, "Strategist", sku, "alert",
              f"Alerte {alert['type']} sur {sku} ({BY_SKU[sku].name}) : {json.dumps(alert['evidence'], default=str)}")
        if self.client is None:
            self._rule_based_fallback(run_id, alert)
            return

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Alerte temps réel : {json.dumps(alert, default=str, ensure_ascii=False)}"},
        ]
        actions: list[dict[str, Any]] = []
        for _ in range(MAX_STEPS):
            response = self.client.chat.completions.create(
                model=settings.openai_model, messages=messages, tools=TOOL_SCHEMAS, tool_choice="auto")
            msg = response.choices[0].message
            if msg.content:
                trace(run_id, "Strategist", sku, "thought" if msg.tool_calls else "decision", msg.content)
            if not msg.tool_calls:
                record_decision(run_id, "Strategist", alert, msg.content or "", actions)
                return
            messages.append(msg.model_dump(exclude_none=True))
            for tc in msg.tool_calls:
                trace(run_id, "Strategist", sku, "action", f"{tc.function.name}({tc.function.arguments})")
                observation = call_tool(tc.function.name, tc.function.arguments)
                trace(run_id, "Strategist", sku, "observation", observation)
                if tc.function.name in ("set_ad_budget", "feature_product", "create_reorder"):
                    actions.append({"tool": tc.function.name, "args": json.loads(tc.function.arguments),
                                    "result": json.loads(observation)})
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": observation})
        record_decision(run_id, "Strategist", alert, "Limite d'étapes atteinte", actions)

    # ------------------------------------------------- repli sans clé OpenAI
    def _rule_based_fallback(self, run_id: str, alert: dict[str, Any]) -> None:
        """Même enquête, raisonnement scripté : la démo reste jouable sans LLM (étiqueté comme tel)."""
        sku, kind = alert["sku"], alert["type"]
        t = lambda k, c: trace(run_id, "Strategist (sans LLM)", sku, k, c)  # noqa: E731
        snap = get_sku_snapshot(sku)
        t("observation", snap)
        actions: list[Any] = []
        if kind == "trend_spike":
            t("thought", "Le signal social est-il réel ? Je regarde l'évolution par fenêtre de 30 min.")
            signal = get_trend_signal(sku)
            t("observation", signal)
            if int(alert["evidence"].get("recent_authors", 0)) < 6:
                t("thought", "Trop peu d'auteurs distincts : probable activité de robots, je n'agis pas.")
            else:
                t("thought", f"Tendance confirmée et marge de {snap['margin_pct']} % : je mise sur ce modèle.")
                actions.append(feature_product(sku, "tendance visuelle confirmée"))
                actions.append(set_ad_budget(sku, round(snap["ads"]["daily_budget"] * 2, 0), "tendance confirmée"))
        fc = forecast_sellout(sku)
        t("observation", fc)
        for size, hours in fc["hours_before_stockout_by_size"].items():
            if hours is not None and hours < 8:
                actions.append(create_reorder(sku, size, 30, f"rupture prévue dans {hours} h"))
        if kind == "burn_without_stock":
            subs = sorted(find_substitutes(sku), key=lambda s: s["total_stock"], reverse=True)
            if subs:
                best = subs[0]
                freed = BY_SKU[sku].base_daily_budget  # budget libéré par la pause Sentinel
                actions.append(set_ad_budget(best["sku"], best["daily_budget"] + freed,
                                             f"réallocation du budget de {sku} (en rupture)"))
        summary = f"{len(actions)} action(s) : " + ", ".join(a.get("status", "?") for a in actions)
        t("decision", summary)
        record_decision(run_id, "Strategist (sans LLM)", alert, summary, actions)
