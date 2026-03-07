.PHONY: lint format test ci

lint:
	ruff check src/

format:
	ruff format src/

test:
	pytest || [ $$? -eq 5 ]

ci: format lint test
