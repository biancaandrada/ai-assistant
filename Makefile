.PHONY: install dev test lint type fmt run docker-build docker-up docker-down clean

install:
	pip install -r requirements.txt

dev:
	pip install -r requirements-dev.txt

run:
	uvicorn app.main:app --reload --ws wsproto --host 0.0.0.0 --port 8000

test:
	pytest -v

lint:
	ruff check app tests

fmt:
	ruff format app tests
	ruff check --fix app tests

type:
	mypy app

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f api

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache .test_chroma
	find . -type d -name __pycache__ -exec rm -rf {} +
