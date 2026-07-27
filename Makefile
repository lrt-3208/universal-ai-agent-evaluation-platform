.PHONY: dev test migrate migrate-new lint format

dev:
	uvicorn agenteval.main:app --reload --host 0.0.0.0 --port 9000

test:
	pytest tests/ -v --cov=src/agenteval --cov-report=term-missing

migrate:
	alembic upgrade head

migrate-new:
	alembic revision --autogenerate -m "$(MSG)"

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

docker-up:
	docker compose up -d

docker-down:
	docker compose down
