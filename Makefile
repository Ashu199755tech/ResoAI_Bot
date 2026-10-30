.PHONY: help setup test test-fast lint format run lakehouse clean

PYTHON ?= ./venv/bin/python
PYTEST ?= ./venv/bin/pytest
RUFF ?= ./venv/bin/ruff
UVICORN ?= ./venv/bin/uvicorn

help:
	@echo "Available commands:"
	@echo "  make setup        - Install dependencies into virtual environment"
	@echo "  make test         - Run test suite"
	@echo "  make test-fast    - Run fast targeted unit tests (lakehouse & API)"
	@echo "  make lint         - Run ruff linter check"
	@echo "  make format       - Format code with ruff"
	@echo "  make lakehouse    - Build DuckDB Medallion Lakehouse & sync holidays"
	@echo "  make run          - Launch ResoAI FastAPI server"
	@echo "  make clean        - Remove caches and temporary files"

setup:
	python3 -m venv venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTEST) tests/test_lakehouse.py tests/test_rag_chain.py tests/test_telegram_bot.py tests/test_web_ui.py -v

test-fast:
	$(PYTEST) tests/test_lakehouse.py -v

lint:
	$(RUFF) check src/ tests/ scripts/

format:
	$(RUFF) format src/ tests/ scripts/

lakehouse:
	$(PYTHON) scripts/build_lakehouse.py --sync-holidays

run:
	$(PYTHON) scripts/run_web.py --port 8000

clean:
	rm -rf __pycache__ .pytest_cache dist build *.egg-info
