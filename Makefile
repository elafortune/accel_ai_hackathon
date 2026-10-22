PY ?= python

.PHONY: install infra demo bench bench-quick stop

install:        ## Environnement Python
	$(PY) -m venv .venv && .venv/bin/pip install -r requirements.txt

infra:          ## Kafka + ClickHouse + PostgreSQL en local
	docker compose up -d

demo: infra     ## Dashboard live sur http://localhost:8000
	.venv/bin/python -m app.main --reset

bench: infra    ## Tableau de résultats complet (results/results.md)
	.venv/bin/python run_simulation.py --seeds 10 --llm-seeds 2

bench-quick: infra
	.venv/bin/python run_simulation.py --seeds 3 --llm-seeds 0

stop:
	docker compose down
