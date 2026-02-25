.PHONY: install check check-all test test-unit test-integration test-e2e test-all ci ci-local ci-local-docker ci-local-docker-down typecheck lint format clean run check-deps security-audit openapi-gate migration-smoke migration-apply pre-commit docker-up docker-down

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pip install pre-commit
	pre-commit install

pre-commit:
	pre-commit run --all-files

check: lint typecheck openapi-gate test

ci: lint typecheck openapi-gate migration-smoke test-all security-audit

test:
	$(MAKE) test-unit

test-unit:
	python -m pytest tests/unit

test-integration:
	python -m pytest tests/integration

test-e2e:
	python -m pytest tests/e2e

test-all:
	python -m pytest --cov=app --cov=engine --cov=core --cov=adapters --cov-report=term-missing --cov-fail-under=99

ci-local: lint check-deps
	python -m pip check
	COVERAGE_FILE=.coverage.unit python -m pytest tests/unit --cov=app --cov=engine --cov=core --cov=adapters --cov-report=
	COVERAGE_FILE=.coverage.integration python -m pytest tests/integration --cov=app --cov=engine --cov=core --cov=adapters --cov-report=
	COVERAGE_FILE=.coverage.e2e python -m pytest tests/e2e --cov=app --cov=engine --cov=core --cov=adapters --cov-report=
	python -m coverage combine .coverage.unit .coverage.integration .coverage.e2e
	python -m coverage report --fail-under=99
	$(MAKE) typecheck

ci-local-docker:
	docker compose -f docker-compose.ci-local.yml up --build --abort-on-container-exit --exit-code-from ci-local ci-local

ci-local-docker-down:
	docker compose -f docker-compose.ci-local.yml down -v --remove-orphans

check-all: lint typecheck test-all

typecheck:
	mypy --config-file mypy.ini

openapi-gate:
	python scripts/openapi_quality_gate.py

migration-smoke:
	python scripts/migration_contract_check.py --mode no-schema

migration-apply:
	python scripts/migration_contract_check.py --mode no-schema

lint:
	ruff check .
	ruff format --check .

format:
	ruff format .

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ['__pycache__', '.pytest_cache', 'htmlcov', '.ruff_cache', '.mypy_cache']]; [pathlib.Path(p).unlink(missing_ok=True) for p in ['.coverage', '.coverage.unit', '.coverage.integration', '.coverage.e2e']]"

run:
	uvicorn main:app --reload --port 8000

check-deps:
	python scripts/dependency_health_check.py --requirements requirements.txt

security-audit:
	python scripts/dependency_health_check.py --requirements requirements.txt

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down
