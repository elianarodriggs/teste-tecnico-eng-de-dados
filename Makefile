.PHONY: up down pipeline pipeline-dag test inspect pdf

up:
	docker compose up -d

down:
	docker compose down

pipeline:
	docker compose --profile pipeline run --rm pipeline all

pipeline-dag:
	docker compose --profile pipeline run --rm --entrypoint python pipeline /app/orchestration/dag_sigmu_daily.py

test:
	docker compose --profile pipeline run --rm --entrypoint pytest pipeline -q

inspect:
	docker compose --profile pipeline run --rm --no-deps --entrypoint python pipeline /app/scripts/inspect_gold.py

pdf:
	npx --yes @marp-team/marp-cli docs/apresentacao.md --pdf --allow-local-files -o docs/apresentacao.pdf
