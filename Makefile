.PHONY: lint format test

lint:
	cd backend && ruff .

format:
	cd backend && black .

test:
	cd backend && pytest
