.PHONY: help setup dev test demo clean deploy

help:
	@echo "AgentOps MVP - Makefile Commands"
	@echo ""
	@echo "  make setup    - Set up development environment"
	@echo "  make dev      - Start development server"
	@echo "  make test     - Run tests"
	@echo "  make demo     - Run demo script"
	@echo "  make clean    - Clean temporary files"
	@echo "  make deploy   - Deploy infrastructure with Terraform"

setup:
	@bash scripts/setup_dev.sh

dev:
	@echo "Starting AgentOps orchestrator..."
	@uvicorn orchestrator.main:app --reload --host 0.0.0.0 --port 8000

test:
	@pytest tests/ -v

test-unit:
	@pytest tests/test_schemas.py -v

test-integration:
	@pytest tests/test_orchestrator_flow.py -v

demo:
	@bash demo/demo.sh

clean:
	@find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
	@echo "✅ Cleaned temporary files"

deploy:
	@cd deploy/terraform && terraform init && terraform apply

deploy-destroy:
	@cd deploy/terraform && terraform destroy

lint:
	@echo "Running linters..."
	@flake8 orchestrator/ tests/ || true
	@black --check orchestrator/ tests/ || true

format:
	@black orchestrator/ tests/

upload-docs:
	@python scripts/upload_docs.py

