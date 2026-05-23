.PHONY: install dev test lint run docker

install:
	pip install -r requirements.txt

dev:
	pip install -r requirements-dev.txt

test:
	pytest tests/ -v --cov=src

lint:
	ruff check src/ tests/

run:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

docker:
	docker-compose -f docker/docker-compose.yml up -d

docker-dev:
	docker-compose -f docker/docker-compose.dev.yml up -d
