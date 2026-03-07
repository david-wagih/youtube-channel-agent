.PHONY: lint format test ci

lint:
	ruff check src/

format:
	ruff format src/

test:
	pytest; code=$$?; [ $$code -eq 5 ] && exit 0 || exit $$code

ci: format lint test
