.PHONY: install lint format fix test ci build

install:
	pip install -e ".[dev]"

# Auto-fix: reformat + apply safe lint fixes
fix:
	ruff format src/
	ruff check --fix src/

# Check only (matches CI — no auto-fix)
lint:
	ruff format --check src/
	ruff check src/

test:
	pytest --tb=short

# Full local CI simulation (check, don't fix)
ci: lint test

build:
	pip install -e .
