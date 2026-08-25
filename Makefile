# Makefile — RevivePay AI
# All targets that haven't been implemented yet print a clear message.
# As each phase is completed, the corresponding target will be filled in.

.PHONY: help setup dev backend frontend seed test lint typecheck eval demo verify \
        clean

# Default shell
SHELL := /bin/bash

# Paths
BACKEND_DIR := backend
FRONTEND_DIR := frontend
VENV         := $(BACKEND_DIR)/.venv
PYTHON       := $(VENV)/bin/python
PIP          := $(VENV)/bin/pip
PYTEST       := $(VENV)/bin/pytest
RUFF         := $(VENV)/bin/ruff
MYPY         := $(VENV)/bin/mypy

# ── Help ─────────────────────────────────────────────────────────────────────

help: ## Show this help message
	@echo ""
	@echo "RevivePay AI — available make targets:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ── Setup ────────────────────────────────────────────────────────────────────

setup: ## Install backend and frontend dependencies (Phase 1)
	@echo "⚙️  [setup] Creating Python virtual environment..."
	@python3.11 -m venv $(VENV) || python3 -m venv $(VENV)
	@echo "⚙️  [setup] Installing backend dependencies..."
	@$(PIP) install --upgrade pip
	@$(PIP) install -r $(BACKEND_DIR)/requirements.txt
	@echo "⚙️  [setup] Installing frontend dependencies..."
	@cd $(FRONTEND_DIR) && npm install
	@echo "✅  [setup] Done. Copy .env.example to .env and edit as needed."

# ── Development Servers ───────────────────────────────────────────────────────

dev: ## Run backend and frontend together in development mode (Phase 2)
	@echo "🔲 [dev] Not yet built — will be available in Phase 2."
	@echo "    Run 'make backend' and 'make frontend' in separate terminals."
	@exit 0

backend: ## Run the FastAPI backend in development mode (Phase 2)
	@echo "🔲 [backend] FastAPI server not yet implemented — available in Phase 2."
	@exit 0

frontend: ## Run the Next.js frontend in development mode (Phase 16)
	@echo "🔲 [frontend] Frontend not yet implemented — available in Phase 16."
	@exit 0

# ── Data ─────────────────────────────────────────────────────────────────────

seed: ## Generate synthetic data and seed the database (Phase 3)
	@echo "🔲 [seed] Synthetic data generation not yet implemented — available in Phase 3."
	@exit 0

# ── Quality Checks ───────────────────────────────────────────────────────────

lint: ## Run ruff lint and format checks (Phase 1)
	@echo "🔍 [lint] Running ruff..."
	@if [ -f $(RUFF) ]; then \
		$(RUFF) check $(BACKEND_DIR)/; \
		$(RUFF) format --check $(BACKEND_DIR)/; \
	else \
		echo "⚠️  ruff not found. Run 'make setup' first."; \
		exit 1; \
	fi

typecheck: ## Run mypy type checker (Phase 1)
	@echo "🔍 [typecheck] Running mypy..."
	@if [ -f $(MYPY) ]; then \
		$(MYPY) $(BACKEND_DIR)/app/; \
	else \
		echo "⚠️  mypy not found. Run 'make setup' first."; \
		exit 1; \
	fi

test: ## Run the pytest test suite (Phase 1)
	@echo "🧪 [test] Running pytest..."
	@if [ -f $(PYTEST) ]; then \
		$(PYTEST) $(BACKEND_DIR)/tests/ -v; \
	else \
		echo "⚠️  pytest not found. Run 'make setup' first."; \
		exit 1; \
	fi

verify: ## Run lint + typecheck + tests + frontend build (full CI check)
	@echo "🔎 [verify] Running full verification suite..."
	@$(MAKE) lint
	@$(MAKE) typecheck
	@$(MAKE) test
	@echo "🔎 [verify] Running frontend build..."
	@if [ -d $(FRONTEND_DIR)/node_modules ]; then \
		cd $(FRONTEND_DIR) && npm run build; \
	else \
		echo "⚠️  Frontend dependencies not installed. Run 'make setup' first."; \
		exit 1; \
	fi
	@echo "✅  [verify] All checks passed."

# ── Evaluation ───────────────────────────────────────────────────────────────

eval: ## Run the counterfactual evaluation against all baselines (Phase 15)
	@echo "🔲 [eval] Evaluation runner not yet implemented — available in Phase 15."
	@exit 0

# ── Demo ─────────────────────────────────────────────────────────────────────

demo: ## Run the full end-to-end demo (Phase 17)
	@echo "🔲 [demo] Full demo not yet assembled — available in Phase 17."
	@echo "    When complete: docker compose up"
	@exit 0

# ── Housekeeping ──────────────────────────────────────────────────────────────

clean: ## Remove generated files, caches and build artifacts
	@echo "🧹 [clean] Removing Python caches..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "🧹 [clean] Removing frontend build artifacts..."
	@rm -rf $(FRONTEND_DIR)/.next $(FRONTEND_DIR)/out
	@echo "✅  [clean] Done."
