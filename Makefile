# AI Warehouse Replenishment Orchestration Demo — developer shortcuts.
# All targets run in MOCK_MODE; no cloud credentials required.

.DEFAULT_GOAL := help
.PHONY: help install backend frontend lint test evals check compose clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Sync backend deps (uv) and install frontend deps (npm)
	uv sync
	cd frontend && npm install

backend: ## Run the FastAPI service on :8080
	uv run uvicorn app.main:app --app-dir src --reload --port 8080

frontend: ## Run the Vite dev server on :5173
	cd frontend && npm run dev

lint: ## Lint the backend with ruff
	uv run ruff check .

test: ## Run unit + integration tests
	uv run pytest -q

evals: ## Run the groundedness + decision-quality eval harness
	uv run python -m tests.evals.run_evals

check: lint test evals ## Run lint, tests, and evals

compose: ## Build and run the full stack with Docker Compose
	docker compose up --build

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache frontend/dist
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
