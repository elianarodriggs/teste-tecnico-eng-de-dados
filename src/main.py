import json
import logging
import sys

from pipeline import Pipeline


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
    etapa = sys.argv[1] if len(sys.argv) > 1 else "all"
    if etapa not in {"all", "bronze", "silver", "gold"}:
        raise SystemExit(f"etapa desconhecida: {etapa}")

    pipeline = Pipeline()
    resumo = {}
    if etapa in {"all", "bronze"}:
        resumo["bronze"] = pipeline.bronze()
    if etapa in {"all", "silver"}:
        resumo["silver"] = pipeline.silver()
    if etapa in {"all", "gold"}:
        resumo["gold"] = pipeline.gold()

    print("PIPELINE_SUMMARY " + json.dumps(resumo, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
