.PHONY: install test lint typecheck dag dag-check guardrails all ci clean build9-core-smoke

UV ?= uv

install:
	$(UV) sync

test:
	$(UV) run pytest tests/ -v --tb=short

test-build1:
	$(UV) run pytest tests/test_interface_contracts/ tests/test_manifest_registry/ tests/test_dag_validator/ tests/test_contract_test_suite/ tests/test_smoke_bootstrap_recovery/ -v --tb=short

test-cov:
	$(UV) run pytest tests/ --cov=src --cov-report=term-missing --cov-report=html

lint:
	$(UV) run ruff check src/ tests/
	$(UV) run ruff format --check src/ tests/

format:
	$(UV) run ruff format src/ tests/
	$(UV) run ruff check --fix src/ tests/

typecheck:
	$(UV) run mypy src/

dag:
	$(UV) run python scripts/run_dag_check.py

dag-check:
	$(UV) run python scripts/run_dag_check.py

guardrails:
	$(UV) run python scripts/run_engineering_guardrails.py

contract-tests:
	$(UV) run python scripts/run_contract_tests.py

smoke-tests:
	$(UV) run python scripts/run_smoke_tests.py

build9-core-smoke:
	$(UV) run python scripts/run_build9_core_smoke.py

all: lint typecheck dag guardrails test

ci: all
	@echo "CI complet - tous les checks passent"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	rm -rf htmlcov .coverage
