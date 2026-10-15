from __future__ import annotations

import argparse
import json
import logging
import sys

from sigmu_pipeline.config import load_config
from sigmu_pipeline.jobs.bronze import run_bronze
from sigmu_pipeline.jobs.gold import run_gold
from sigmu_pipeline.jobs.silver import run_silver

STAGES = {
    "bronze": run_bronze,
    "silver": run_silver,
    "gold": run_gold,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pipeline SIGMU Bronze → Silver → Gold")
    parser.add_argument("stage", choices=[*STAGES, "all"])
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )
    cfg = load_config()
    stages = list(STAGES) if args.stage == "all" else [args.stage]
    summaries = {}
    for stage in stages:
        logging.info("iniciando etapa %s", stage)
        summaries[stage] = STAGES[stage](cfg)
        logging.info("etapa %s concluída", stage)
    print("PIPELINE_SUMMARY " + json.dumps(summaries, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
