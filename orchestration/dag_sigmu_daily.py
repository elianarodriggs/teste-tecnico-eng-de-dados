"""DAG linear no estilo de um pipeline orquestrado.

Tarefas e dependências:

    landing_bronze >> curated_silver >> consumo_gold

Cada tarefa chama o mesmo job da CLI. Falha numa etapa interrompe as
seguintes. Reexecutar o DAG sobrescreve a partição snapshot_date.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass

from sigmu_pipeline.cli import main as cli_main

logger = logging.getLogger(__name__)


@dataclass
class Task:
    name: str
    upstream: list[str]
    run: Callable[[], None]


def _run_cli(stage: str) -> None:
    code = cli_main([stage])
    if code != 0:
        raise RuntimeError(f"etapa {stage} retornou {code}")


TASKS = {
    "landing_bronze": Task("landing_bronze", [], lambda: _run_cli("bronze")),
    "curated_silver": Task("curated_silver", ["landing_bronze"], lambda: _run_cli("silver")),
    "consumo_gold": Task("consumo_gold", ["curated_silver"], lambda: _run_cli("gold")),
}

ORDER = ["landing_bronze", "curated_silver", "consumo_gold"]


def run_dag() -> None:
    done: set[str] = set()
    for name in ORDER:
        task = TASKS[name]
        missing = [item for item in task.upstream if item not in done]
        if missing:
            raise RuntimeError(f"{name} bloqueada; dependências ausentes: {missing}")
        logger.info("task start %s", name)
        task.run()
        done.add(name)
        logger.info("task success %s", name)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )
    run_dag()
