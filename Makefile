.PHONY: install dev lint test test-cov run dashboard docker docker-down evaluate clean

# ── 설치 ──
install:
	pip install -e .

dev:
	pip install -e ".[dev]"
	pre-commit install

# ── 코드 품질 ──
lint:
	ruff check src/ tests/ cli/ eval/

lint-fix:
	ruff check --fix src/ tests/ cli/ eval/

format:
	ruff format src/ tests/ cli/ eval/

# ── 테스트 ──
test:
	pytest -v

test-cov:
	pytest --cov=src --cov-report=html --cov-report=term -v

# ── 실행 ──
run:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

dashboard:
	streamlit run dashboard/app.py

# ── 평가 ──
evaluate:
	python -m eval.evaluate

# ── Docker ──
docker:
	docker-compose up --build -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f api

# ── 정리 ──
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage coverage.xml
