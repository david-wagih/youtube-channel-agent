.PHONY: lint format test ci build

lint:
	ruff check src/

format:
	ruff format src/

test:
	pytest || [ $$? -eq 5 ]

ci: format lint test

build:
	pip install -e .
