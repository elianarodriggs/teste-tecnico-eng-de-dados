.PHONY: up down pipeline test

up:
	docker compose up -d

down:
	docker compose down

pipeline:
	docker compose --profile pipeline run --rm pipeline all

test:
	docker compose --profile pipeline run --rm --entrypoint pytest pipeline -q

inspect:
	docker compose --profile pipeline run --rm --no-deps --entrypoint python pipeline /app/scripts/inspect_gold.py
