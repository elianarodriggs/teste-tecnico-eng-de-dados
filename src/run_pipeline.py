import json
import logging
import sys

from build_gold import run_gold
from build_silver import run_silver
from ingest import run_ingest


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    summary = {}
    if stage in {"all", "bronze"}:
        summary["bronze"] = run_ingest()
    if stage in {"all", "silver"}:
        summary["silver"] = run_silver()
    if stage in {"all", "gold"}:
        summary["gold"] = run_gold()
    if stage not in {"all", "bronze", "silver", "gold"}:
        raise SystemExit(f"etapa desconhecida: {stage}")
    print("PIPELINE_SUMMARY " + json.dumps(summary, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
