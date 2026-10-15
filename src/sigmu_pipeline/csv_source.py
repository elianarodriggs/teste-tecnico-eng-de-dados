from __future__ import annotations

import logging

import pandas as pd
import requests

logger = logging.getLogger(__name__)

DELIMITER = ";"


def download_csv(url: str, timeout: int = 180) -> bytes:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.content


def _is_type_mask(line: str) -> bool:
    compact = line.replace(DELIMITER, "").strip()
    return bool(compact) and set(compact) <= {"-"}


def parse_sigmu_csv(raw: bytes) -> tuple[pd.DataFrame, int]:
    """Lê o CSV do SIGMU.

    A Bronze guarda os bytes originais. Esta função só roda na Silver:
    Latin-1, delimitador ';', ignora a linha de máscara e descarta
    linhas cuja contagem de campos não fecha com o cabeçalho.
    """
    text = raw.decode("latin-1").replace("\x00", "")
    lines = text.splitlines()
    if not lines:
        raise ValueError("CSV vazio")

    columns = lines[0].split(DELIMITER)
    expected = len(columns)
    start = 2 if len(lines) > 1 and _is_type_mask(lines[1]) else 1

    rows: list[list[str]] = []
    dropped = 0
    for line in lines[start:]:
        if not line.strip():
            dropped += 1
            continue
        if line.count(DELIMITER) != expected - 1:
            dropped += 1
            continue
        rows.append(line.split(DELIMITER))

    frame = pd.DataFrame(rows, columns=columns)
    logger.info("csv lido: %s colunas, %s linhas, %s descartadas", expected, len(frame), dropped)
    return frame, dropped
