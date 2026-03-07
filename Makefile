.PHONY: lint format test ci

lint:
	ruff check src/

format:
	ruff format src/

test:
	pytest

ci: format lint test
