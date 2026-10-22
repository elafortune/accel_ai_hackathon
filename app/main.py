"""Point d'entrée : lance simulateur, ingestion, détection, agents et dashboard dans un seul process.

    python -m app.main            # démarre tout (http://localhost:8000)
    python -m app.main --reset    # recrée les tables avant de démarrer
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse

from app import bus
from app.agents import ActionExecutor, AgentWorker
from app.config import Topics, settings
from app.detector import Detector
from app.ingest import Ingestor
from app.schema import reset_all
from app.simulator import Simulator
from app.stores import ch, pg

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(threadName)s %(levelname)s %(message)s")
for noisy in ("httpx", "kafka"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

app = FastAPI(title="Fashion live agent")
sim: Simulator
agents: AgentWorker
ingestor: Ingestor
control = None


@app.get("/")
def index() -> FileResponse:
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.post("/scenario/{kind}")
def scenario(kind: str, sku: str | None = None) -> dict[str, str]:
    payload = {"type": kind, "sku": sku}
    control.send(Topics.CONTROL, payload)
    control.flush()
    sim.inject(payload)
    return {"status": "injecté", "scenario": kind}


def _top_trends() -> list[dict]:
    return ch.query("""
        WITH (SELECT max(sim_ts) FROM social) AS now
        SELECT matched_sku AS sku, countIf(similarity >= 0.8) AS similar_posts_1h,
               uniqExactIf(author, similarity >= 0.8) AS authors
        FROM social WHERE sim_ts > now - INTERVAL 1 HOUR
        GROUP BY sku ORDER BY similar_posts_1h DESC LIMIT 5""")


@app.get("/stream")
async def stream() -> StreamingResponse:
    async def events():
        last_id = 0
        while True:
            rows = pg().run("SELECT id, ts, agent, sku, kind, content FROM agent_trace WHERE id > :i ORDER BY id",
                            i=last_id)
            if rows:
                last_id = rows[-1]["id"]
            try:
                trends = _top_trends()
            except Exception:
                trends = []
            rt = agents.reaction_times
            payload = {
                **sim.snapshot(),
                "trace": [{**r, "ts": r["ts"].isoformat()} for r in rows],
                "trends": trends,
                "sentinel_reaction_s": round(sum(rt) / len(rt), 2) if rt else None,
                "rows_ingested": ingestor.rows_ingested,
                "llm": settings.openai_model if settings.llm_enabled else "désactivé (repli à règles)",
            }
            yield f"data: {json.dumps(payload, default=str, ensure_ascii=False)}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(events(), media_type="text/event-stream")


def main() -> None:
    global sim, agents, ingestor, control
    if "--reset" in sys.argv:
        reset_all()
    bus.ensure_topics()
    control = bus.producer()
    ingestor = Ingestor()
    sim = Simulator()
    agents = AgentWorker(sim)
    detector = Detector(clock_minutes=lambda: sim.tick * sim.minutes)
    for component in (ingestor, sim, detector, ActionExecutor(sim), agents):
        component.start()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


if __name__ == "__main__":
    main()
