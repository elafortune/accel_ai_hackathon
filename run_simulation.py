"""Benchmark reproductible : produit le tableau de résultats comparatifs.

Même scénario, mêmes seeds, plusieurs stratégies :
  - baseline_j1    : règles quotidiennes sur les données de la veille (pratique actuelle) ;
  - realtime_rules : règles fixes déclenchées par les alertes temps réel (sans LLM) ;
  - agent          : Sentinel + Strategist LLM (si OPENAI_API_KEY est défini).

Le simulateur avance pas à pas ; les événements sont écrits dans ClickHouse, la détection
se fait en SQL ClickHouse et les agents lisent ClickHouse/Postgres via leurs outils.
Pendant qu'un agent réfléchit, le temps simulé est figé : un pas = 10 min simulées,
un appel LLM = quelques secondes réelles, l'hypothèse est donc réaliste.

    python run_simulation.py                       # Tableau A (10 seeds, sans LLM) + B (2 seeds avec LLM)
    python run_simulation.py --seeds 3 --llm-seeds 0
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

from app import tools
from app.agents import AgentWorker
from app.config import Topics, settings
from app.detector import AlertGate, scan
from app.schema import reset_all
from app.simulator import REALTIME_WORLDS, Simulator
from app.stores import ch, pg

# Scénario commun : (heure simulée, événement)
SCHEDULE_HOURS = [
    (1, {"type": "viral", "sku": "SKU-0712"}),        # vraie vague virale
    (3, {"type": "stockout", "sku": "SKU-1104"}),     # rupture M/L
    (5, {"type": "fake_trend", "sku": "SKU-2230"}),   # pic de posts de 3 comptes robots
]
METRICS = [
    ("profit", "Profit (marge − pub − surcoût réassort)", "€"),
    ("revenue", "Chiffre d'affaires", "€"),
    ("ad_spend", "Dépense pub", "€"),
    ("wasted_ad_spend", "Pub gaspillée sur tailles épuisées", "€"),
    ("lost_margin", "Marge perdue (ruptures)", "€"),
    ("viral_units", "Ventes du modèle viral (SKU-0712)", "u"),
    ("fake_trend_extra_spend", "Pub supplémentaire sur la fausse tendance (SKU-2230)", "€"),
    ("reorder_premium", "Surcoût réassorts express", "€"),
]
LABELS = {"baseline_j1": "Règles J-1", "realtime_rules": "Règles temps réel", "agent": "Agent LLM"}


def run_once(seed: int, strategies: list[str], days: int, use_llm: bool) -> dict[str, Any]:
    reset_all()
    sim = Simulator(seed=seed, worlds=strategies, publish=False)
    tools.set_action_sink(sim.apply_action)
    worker = AgentWorker(sim, use_llm=use_llm)
    gate = AlertGate(lambda: sim.tick * sim.minutes)
    schedule = {sim.hours_to_ticks(h): sc for h, sc in SCHEDULE_HOURS}
    realtime = [w for w in strategies if w in REALTIME_WORLDS]
    alerts_seen = 0

    for tick in range(days * sim.ticks_per_day):
        if tick in schedule:
            sim.inject(schedule[tick])
        out = sim.step()
        for topic, rows in out.items():
            ch.insert(Topics.INGESTED[topic], rows)
        for world in realtime:
            for alert in scan(world, gate):
                alerts_seen += 1
                worker.handle(alert)

    results = {}
    reference_fake_spend = sim.worlds["baseline_j1"].spend_by_sku.get("SKU-2230", 0.0)
    for name, w in sim.worlds.items():
        results[name] = {
            **{k: round(v, 2) for k, v in w.kpi.items()},
            "profit": round(w.profit, 2),
            "viral_units": w.units_by_sku.get("SKU-0712", 0),
            "fake_trend_extra_spend": round(w.spend_by_sku.get("SKU-2230", 0.0) - reference_fake_spend, 2),
        }
    decisions = pg().run("SELECT agent, count(*) AS n FROM decisions GROUP BY agent")
    return {"seed": seed, "llm": use_llm and settings.llm_enabled, "alerts": alerts_seen,
            "decisions": {d["agent"]: d["n"] for d in decisions}, "worlds": results}


def summarize(runs: list[dict[str, Any]], strategies: list[str]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for key, _, _ in METRICS:
        summary[key] = {}
        for s in strategies:
            values = [r["worlds"][s][key] for r in runs]
            summary[key][s] = (statistics.mean(values), statistics.pstdev(values) if len(values) > 1 else 0.0)
    gains = [r["worlds"][strategies[-1]]["profit"] - r["worlds"]["baseline_j1"]["profit"] for r in runs]
    summary["wins"] = sum(g > 0 for g in gains)
    return summary


def to_markdown(title: str, runs: list[dict[str, Any]], strategies: list[str]) -> str:
    s = summarize(runs, strategies)
    vs_rules = strategies[-1] == "agent" and "realtime_rules" in strategies
    head = "| Métrique | " + " | ".join(LABELS[x] for x in strategies) + " | Écart vs règles J-1 |"
    if vs_rules:
        head += " Écart agent vs règles temps réel |"
    lines = [f"### {title}", "", f"{len(runs)} seed(s) · moyenne ± écart-type · "
             f"{LABELS[strategies[-1]]} > règles J-1 sur le profit dans {s['wins']}/{len(runs)} runs", "", head,
             "|" + "---|" * (len(strategies) + 2 + vs_rules)]
    for key, label, unit in METRICS:
        cells = []
        for x in strategies:
            m, sd = s[key][x]
            cells.append(f"{m:,.0f} ± {sd:,.0f} {unit}".replace(",", " "))
        best = strategies[-1]
        delta = s[key][best][0] - s[key]["baseline_j1"][0]
        ref = s[key]["baseline_j1"][0]
        pct = f" ({100 * delta / abs(ref):+.0f} %)" if ref else ""
        row = f"| {label} | " + " | ".join(cells) + f" | {delta:+,.0f} {unit}{pct} |".replace(",", " ")
        if vs_rules:
            row += f" {s[key]['agent'][0] - s[key]['realtime_rules'][0]:+,.0f} {unit} |".replace(",", " ")
        lines.append(row)
    return "\n".join(lines) + "\n"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=10, help="seeds rapides sans LLM (tableau A)")
    parser.add_argument("--llm-seeds", type=int, default=2, help="seeds avec l'agent LLM (tableau B)")
    parser.add_argument("--days", type=int, default=2, help="jours simulés par run")
    args = parser.parse_args()

    out_dir = Path("results")
    out_dir.mkdir(exist_ok=True)
    results_json = out_dir / "results.json"
    # On conserve les tableaux déjà calculés : relancer B seul ne doit pas effacer A
    raw: dict[str, Any] = json.loads(results_json.read_text(encoding="utf-8")) if results_json.exists() else {}

    if args.seeds:
        strategies = ["baseline_j1", "realtime_rules"]
        runs = []
        for seed in range(args.seeds):
            t0 = time.time()
            runs.append(run_once(seed, strategies, args.days, use_llm=False))
            print(f"[A] seed {seed} terminé en {time.time() - t0:.0f} s")
        raw["A"] = runs

    if args.llm_seeds:
        if not settings.llm_enabled:
            print("OPENAI_API_KEY absent : tableau B ignoré.")
        else:
            strategies = ["baseline_j1", "realtime_rules", "agent"]
            runs = []
            for seed in range(100, 100 + args.llm_seeds):
                t0 = time.time()
                runs.append(run_once(seed, strategies, args.days, use_llm=True))
                print(f"[B] seed {seed} terminé en {time.time() - t0:.0f} s")
            raw["B"] = runs

    report = ["# Résultats comparatifs", "",
              f"Scénario : vague virale (h+1), rupture M/L (h+3), fausse tendance robots (h+5) ; "
              f"{args.days} jours simulés par run.", ""]
    if "A" in raw:
        report.append(to_markdown("Tableau A : valeur du temps réel (règles temps réel vs règles J-1)",
                                  raw["A"], ["baseline_j1", "realtime_rules"]))
    if "B" in raw:
        report.append(to_markdown("Tableau B : valeur du raisonnement (agent LLM vs règles)",
                                  raw["B"], ["baseline_j1", "realtime_rules", "agent"]))
    (out_dir / "results.md").write_text("\n".join(report), encoding="utf-8")
    results_json.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
