SITE_DIR := site

.PHONY: help install test report open clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

install: ## Install skills interactively
	./install.sh

test: ## Run tests and generate HTML report
	@mkdir -p $(SITE_DIR)/runs/local/local
	cd tests && pip install -e . && pytest -v \
		--rootdir . -c pyproject.toml \
		--html $(CURDIR)/$(SITE_DIR)/runs/local/local/pytest-local.html \
		--self-contained-html; \
	rc=$$?; \
	python $(CURDIR)/.github/scripts/generate-pages-index.py $(CURDIR)/$(SITE_DIR); \
	exit $$rc

open: ## Open test report in browser
	@if [ -f $(SITE_DIR)/index.html ]; then \
		xdg-open $(SITE_DIR)/index.html 2>/dev/null || open $(SITE_DIR)/index.html; \
	else \
		echo "No report found. Run 'make test' first."; exit 1; \
	fi

clean: ## Remove build artifacts and reports
	rm -rf $(SITE_DIR) tests/build tests/claude_skills_tests.egg-info tests/__pycache__ tests/**/__pycache__
