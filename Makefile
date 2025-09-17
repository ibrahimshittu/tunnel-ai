.PHONY: help install dev-install test lint format clean run docker-build docker-run

help:
	@echo "Available commands:"
	@echo "  make install      - Install production dependencies"
	@echo "  make dev-install  - Install development dependencies"
	@echo "  make test        - Run tests"
	@echo "  make lint        - Run linters"
	@echo "  make format      - Format code"
	@echo "  make clean       - Clean up temporary files"
	@echo "  make run         - Start the API server"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-run  - Run Docker container"

install:
	pip install --upgrade pip
	pip install -r requirements.txt
	playwright install

dev-install:
	pip install --upgrade pip
	pip install -r requirements.txt
	pip install -e ".[dev]"
	playwright install
	pre-commit install

test:
	pytest tests/ -v --cov=agents --cov=api --cov=core --cov=orchestrator

lint:
	black --check .
	isort --check-only .
	flake8 .
	mypy .

format:
	black .
	isort .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ htmlcov/ .coverage coverage.xml

run:
	python -m api.main

docker-build:
	docker build -t tunnel-ai:latest .

docker-run:
	docker run -p 8000:8000 --env-file .env tunnel-ai:latest

setup: dev-install
	@echo "Setting up pre-commit hooks..."
	pre-commit install
	@echo "Creating necessary directories..."
	mkdir -p logs screenshots videos tests/generated
	@echo "Setup complete!"

check: lint test
	@echo "All checks passed!"