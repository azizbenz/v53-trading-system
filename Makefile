.PHONY: test lint typecheck dag-check ci clean install build9-core-smoke

PYTHON ?= python

# Installation
install:
	$(PYTHON) -m pip install -e ".[dev]"

# Tests
test:
	$(PYTHON) -m pytest tests/ -v --tb=short

test-build1:
	$(PYTHON) -m pytest tests/test_interface_contracts/ tests/test_manifest_registry/ tests/test_dag_validator/ tests/test_contract_test_suite/ tests/test_smoke_bootstrap_recovery/ -v --tb=short

test-cov:
	$(PYTHON) -m pytest tests/ --cov=src --cov-report=term-missing --cov-report=html

# Qualité
lint:
	$(PYTHON) -m ruff check src/ tests/
	$(PYTHON) -m ruff format --check src/ tests/

format:
	$(PYTHON) -m ruff format src/ tests/
	$(PYTHON) -m ruff check --fix src/ tests/

typecheck:
	$(PYTHON) -m mypy src/

# Architecture
dag-check:
	$(PYTHON) scripts/run_dag_check.py

contract-tests:
	$(PYTHON) scripts/run_contract_tests.py

smoke-tests:
	$(PYTHON) scripts/run_smoke_tests.py

build9-core-smoke:
	$(PYTHON) scripts/run_build9_core_smoke.py

# CI complet
ci: lint typecheck test dag-check
	@echo "✅ CI complet — tous les checks passent"

# Nettoyage
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	rm -rf htmlcov .coverage
