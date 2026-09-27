.PHONY: setup lint format test up down logs api pipeline loadtest

setup:      ## install Python 3.11 + locked dependencies
	uv sync

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

test: lint
	uv run pytest -q

up:         ## start API, MLflow, Prefect, Prometheus, Grafana
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

api:        ## run API locally without Docker
	uv run uvicorn triage.serving.app:app --reload --port 8000

pipeline:   ## TODO(pipeline workstream): end-to-end Prefect DAG
	@echo "not implemented yet"

loadtest:   ## TODO(serving workstream): Locust p50/p95/throughput
	@echo "not implemented yet"
