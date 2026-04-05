.PHONY: help install dev-setup lint lint-fix format type-check test clean all

help:
	@echo "Available commands:"
	@echo "  make install       - Install project dependencies"
	@echo "  make dev-setup     - Install dev dependencies"
	@echo "  make lint          - Check code with ruff"
	@echo "  make lint-fix      - Fix linting issues with ruff"
	@echo "  make format        - Format code with ruff"
	@echo "  make type-check    - Run mypy type checking"
	@echo "  make test          - Run pytest tests"
	@echo "  make all           - Run lint, type-check, and test"
	@echo "  make clean         - Remove build artifacts and cache files"

install:
	uv sync

dev-setup:
	uv sync --all-extras

lint:
	uv run ruff check src/ tests/

lint-fix:
	uv run ruff check --fix src/ tests/

format:
	uv run ruff format src/ tests/

type-check:
	uv run mypy src/

test:
	uv run pytest -v

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .ruff_cache
	rm -rf build/ dist/ *.egg-info 2>/dev/null || true

all: lint type-check test
	@echo "All checks passed!"
