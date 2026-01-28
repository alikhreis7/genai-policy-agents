.PHONY: install test run clean lint help

# Default target
help:
	@echo "Available commands:"
	@echo "  make install  - Create venv and install dependencies"
	@echo "  make test     - Run all tests"
	@echo "  make run      - Run interactive demo"
	@echo "  make demo     - Run demo with sample query"
	@echo "  make lint     - Run linter (ruff)"
	@echo "  make clean    - Remove cache and build files"

# Install dependencies
install:
	python -m venv venv
	. venv/bin/activate && pip install -r requirements.txt

# Run tests
test:
	. venv/bin/activate && python -m pytest tests/ -v

# Run interactive mode
run:
	. venv/bin/activate && python -m src.main

# Run demo with sample queries
demo:
	@echo "=== Demo 1: Policy Lookup ==="
	. venv/bin/activate && python -m src.main "Can we store PII in Redis?"
	@echo ""
	@echo "=== Demo 2: Decision Support ==="
	. venv/bin/activate && python -m src.main "Is it acceptable to bypass the API gateway for internal services?"
	@echo ""
	@echo "=== Demo 3: Security Query ==="
	. venv/bin/activate && python -m src.main "What are the authentication requirements for production systems?"

# Lint code
lint:
	. venv/bin/activate && ruff check src/ tests/

# Clean up
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .coverage htmlcov/ 2>/dev/null || true
