.PHONY: test lint typecheck dag-check ci clean install

# Installation
install:
	pip install -e ".[dev]"

# Tests
test:
	pytest tests/ -v --tb=short

test-build1:
	pytest tests/test_interface_contracts/ tests/test_manifest_registry/ tests/test_dag_validator/ tests/test_contract_test_suite/ tests/test_smoke_bootstrap/ -v --tb=short

test-cov:
	pytest tests/ --cov=src --cov-report=term-missing --cov-report=html

# Qualité
lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

typecheck:
	mypy src/

# Architecture
dag-check:
	python scripts/run_dag_check.py

contract-tests:
	python scripts/run_contract_tests.py

smoke-tests:
	python scripts/run_smoke_tests.py

# CI complet
ci: lint typecheck test dag-check
	@echo "✅ CI complet — tous les checks passent"

# Nettoyage
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	rm -rf htmlcov .coverage
