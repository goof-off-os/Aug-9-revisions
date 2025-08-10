# Makefile for ProposalOS RGE
# Run 'make help' to see available commands

.PHONY: help install test lint format type-check security clean audit all quality fix

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)ProposalOS RGE - Development Commands$(NC)"
	@echo "========================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-15s$(NC) %s\n", $$1, $$2}'

install: ## Install all dependencies including dev tools
	@echo "$(BLUE)Installing dependencies...$(NC)"
	pip install --upgrade pip
	pip install -e ".[dev,test]" 2>/dev/null || pip install pydantic fastapi python-dateutil pybreaker redis
	pip install pre-commit black ruff mypy pytest pytest-cov isort bandit
	pre-commit install
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

test: ## Run all tests with coverage
	@echo "$(BLUE)Running tests...$(NC)"
	pytest -q --cov=proposalos_rge --cov-report=term-missing
	@echo "$(GREEN)✓ Tests complete$(NC)"

test-fast: ## Run tests without coverage (faster)
	@echo "$(BLUE)Running tests (fast mode)...$(NC)"
	pytest -q
	@echo "$(GREEN)✓ Tests complete$(NC)"

lint: ## Run linting checks (ruff)
	@echo "$(BLUE)Running linter...$(NC)"
	ruff check .
	@echo "$(GREEN)✓ Linting complete$(NC)"

format: ## Format code with black and isort
	@echo "$(BLUE)Formatting code...$(NC)"
	black .
	isort .
	@echo "$(GREEN)✓ Formatting complete$(NC)"

format-check: ## Check formatting without making changes
	@echo "$(BLUE)Checking formatting...$(NC)"
	black --check .
	isort --check-only .
	@echo "$(GREEN)✓ Format check complete$(NC)"

type-check: ## Run type checking with mypy
	@echo "$(BLUE)Running type checker...$(NC)"
	mypy proposalos_rge --ignore-missing-imports
	@echo "$(GREEN)✓ Type checking complete$(NC)"

security: ## Run security checks with bandit
	@echo "$(BLUE)Running security scan...$(NC)"
	bandit -r proposalos_rge -ll
	@echo "$(GREEN)✓ Security scan complete$(NC)"

audit: ## Run project audit script
	@echo "$(BLUE)Running project audit...$(NC)"
	python "project_audit (1).py" --root . --out project_audit_report.md
	@echo "$(GREEN)✓ Audit complete - see project_audit_report.md$(NC)"

clean: ## Clean up generated files and caches
	@echo "$(BLUE)Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/ 2>/dev/null || true
	rm -rf dist/ build/ 2>/dev/null || true
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

fix: ## Auto-fix issues (formatting, imports, simple linting)
	@echo "$(BLUE)Auto-fixing issues...$(NC)"
	black .
	isort .
	ruff check . --fix
	@echo "$(GREEN)✓ Auto-fix complete$(NC)"

quality: lint format-check type-check security ## Run all quality checks
	@echo "$(GREEN)✓ All quality checks passed$(NC)"

all: clean install quality test ## Run everything (clean, install, quality, test)
	@echo "$(GREEN)✓ All tasks complete$(NC)"

pre-commit: ## Run pre-commit hooks on all files
	@echo "$(BLUE)Running pre-commit hooks...$(NC)"
	pre-commit run --all-files
	@echo "$(GREEN)✓ Pre-commit checks complete$(NC)"

# Development shortcuts
dev: format lint test-fast ## Quick development cycle (format, lint, test)
	@echo "$(GREEN)✓ Development checks complete$(NC)"

check: quality test ## Run all checks (quality + tests)
	@echo "$(GREEN)✓ All checks passed$(NC)"

# Docker commands (if needed)
docker-build: ## Build Docker image
	@echo "$(BLUE)Building Docker image...$(NC)"
	docker build -t proposalos-rge:latest .
	@echo "$(GREEN)✓ Docker image built$(NC)"

docker-run: ## Run Docker container
	@echo "$(BLUE)Running Docker container...$(NC)"
	docker run -p 8000:8000 proposalos-rge:latest
	
# Documentation
docs: ## Generate documentation
	@echo "$(BLUE)Generating documentation...$(NC)"
	python -m pydoc -w proposalos_rge
	@echo "$(GREEN)✓ Documentation generated$(NC)"

# Testing specific components
test-rge: ## Test only RGE components
	@echo "$(BLUE)Testing RGE components...$(NC)"
	python test_proposalos_rge.py
	@echo "$(GREEN)✓ RGE tests complete$(NC)"

test-integration: ## Run integration tests
	@echo "$(BLUE)Running integration tests...$(NC)"
	pytest -m integration -v
	@echo "$(GREEN)✓ Integration tests complete$(NC)"

# Registry operations
registry-list: ## List all registered templates
	@echo "$(BLUE)Listing registered templates...$(NC)"
	@python -c "from registry_bootstrap import list_available_templates; list_available_templates()"

registry-validate: ## Validate all templates can load
	@echo "$(BLUE)Validating template registry...$(NC)"
	@python -c "from registry_bootstrap import validate_all_templates, create_default_registry; r = create_default_registry(); results = validate_all_templates(r); print('✅ All valid' if all(results.values()) else f'❌ Failed: {[k for k,v in results.items() if not v]}')"

# Git hooks
hooks: ## Install git hooks
	@echo "$(BLUE)Installing git hooks...$(NC)"
	pre-commit install
	pre-commit install --hook-type commit-msg
	@echo "$(GREEN)✓ Git hooks installed$(NC)"

# Help aliases
h: help
?: help