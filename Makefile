.PHONY: lint format test

lint:
	ruff .

format:
	black .

test:
	pytest
