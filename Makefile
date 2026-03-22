SITE_DIR := site
MODELS ?= weakest mid strongest

.PHONY: help install test test-fw test-all open clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

install: ## Install skills interactively
	./install.sh

test-fw: ## Run framework unit tests
	cd test_fw && pip install -e . && pytest tests/ -v

test: ## Run skill tests for all model tiers (override with MODELS="weakest mid")
	cd tests && pip install -e ../test_fw && pip install -e . && \
	fail=0; \
	for tier in $(MODELS); do \
		echo ""; echo "========== $$tier =========="; echo ""; \
		pytest -v \
			--model $$tier \
			--rootdir . -c pyproject.toml \
			--html reports/pytest-$$tier.html \
			--self-contained-html \
			skills/ \
		|| fail=1; \
		mkdir -p $(CURDIR)/$(SITE_DIR)/runs/local/$$tier; \
		cp reports/*-$$tier.html reports/*-$$tier.json \
			$(CURDIR)/$(SITE_DIR)/runs/local/$$tier/ 2>/dev/null || true; \
		cp reports/pytest-$$tier.html \
			$(CURDIR)/$(SITE_DIR)/runs/local/$$tier/ 2>/dev/null || true; \
	done; \
	python $(CURDIR)/.github/scripts/generate-pages-index.py $(CURDIR)/$(SITE_DIR); \
	exit $$fail

test-all: test-fw test ## Run all tests (framework + skills)

open: ## Open test report in browser
	@if [ -f $(SITE_DIR)/index.html ]; then \
		xdg-open $(SITE_DIR)/index.html 2>/dev/null || open $(SITE_DIR)/index.html; \
	else \
		echo "No report found. Run 'make test' first."; exit 1; \
	fi

clean: ## Remove build artifacts and reports
	rm -rf $(SITE_DIR) tests/build tests/claude_skills_tests.egg-info tests/__pycache__ tests/**/__pycache__ test_fw/build test_fw/src/*.egg-info
