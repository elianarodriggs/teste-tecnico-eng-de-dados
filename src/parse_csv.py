from __future__ import annotations

import pandas as pd

from sources import DATE_COLUMNS, NUMBER_COLUMNS

DELIMITER = ";"


def _is_mask(line: str) -> bool:
    compact = line.replace(DELIMITER, "").strip()
    return bool(compact) and set(compact) <= {"-"}


def parse_csv(raw: bytes) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Lê o CSV do SIGMU.

    A Bronze guarda os bytes originais. Aqui a linha de máscara é ignorada
    e a linha cuja contagem de campos não fecha vai para quarentena.
    """
    null_bytes = raw.count(b"\x00")
    text = raw.decode("latin-1").replace("\x00", "")
    lines = text.splitlines()
    if not lines:
        raise ValueError("CSV vazio")

    header = lines[0].split(DELIMITER)
    expected = len(header)
    start = 2 if len(lines) > 1 and _is_mask(lines[1]) else 1

    rows: list[list[str]] = []
    rejected: list[dict] = []
    for index, line in enumerate(lines[start:], start=start + 1):
        if not line.strip():
            rejected.append({"line_number": index, "reason": "linha_vazia", "raw_line": line})
            continue
        if line.count(DELIMITER) != expected - 1:
            rejected.append({"line_number": index, "reason": "contagem_de_campos", "raw_line": line[:500]})
            continue
        rows.append(line.split(DELIMITER))

    frame = pd.DataFrame(rows, columns=header)
    quarantine = pd.DataFrame(rejected, columns=["line_number", "reason", "raw_line"])
    info = {"null_bytes_removed": null_bytes, "columns": expected, "mask_skipped": start == 2}
    return frame, quarantine, info


def blank_to_null(frame: pd.DataFrame) -> pd.DataFrame:
    cleaned = frame.copy()
    for column in cleaned.columns:
        text = cleaned[column].astype("string").str.strip()
        cleaned[column] = text.mask(text == "", pd.NA)
    return cleaned


def parse_number(series: pd.Series) -> tuple[pd.Series, int]:
    text = series.astype("string").str.strip()
    text = text.mask(text == "", pd.NA)
    has_comma = text.str.contains(",", na=False)
    normalized = text.where(~has_comma, text.str.replace(".", "", regex=False).str.replace(",", ".", regex=False))
    number = pd.to_numeric(normalized, errors="coerce")
    invalid = int((text.notna() & number.isna()).sum())
    return number, invalid


def apply_types(table: str, frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    typed = blank_to_null(frame)
    metrics = {"invalid_dates": {}, "invalid_numbers": {}}
    for column in DATE_COLUMNS.get(table, []):
        if column not in typed.columns:
            continue
        original = typed[column]
        parsed = pd.to_datetime(original, errors="coerce")
        invalid = int((original.notna() & parsed.isna()).sum())
        typed[column] = parsed
        metrics["invalid_dates"][column] = invalid
    for column in NUMBER_COLUMNS.get(table, []):
        if column not in typed.columns:
            continue
        parsed, invalid = parse_number(typed[column])
        typed[column] = parsed
        metrics["invalid_numbers"][column] = invalid
    return typed, metrics


def deduplicate(frame: pd.DataFrame, primary_key: list[str]) -> tuple[pd.DataFrame, dict]:
    metrics = {"null_keys": 0, "exact_duplicates": 0, "divergent_duplicates": 0}
    if not primary_key or any(column not in frame.columns for column in primary_key):
        return frame, metrics

    null_key = frame[primary_key].isna().any(axis=1)
    metrics["null_keys"] = int(null_key.sum())
    keyed = frame.loc[~null_key].copy()
    exact = keyed.duplicated(keep="first")
    metrics["exact_duplicates"] = int(exact.sum())
    keyed = keyed.loc[~exact]
    key_dup = keyed.duplicated(subset=primary_key, keep=False)
    metrics["divergent_duplicates"] = int(keyed.loc[key_dup, primary_key].drop_duplicates().shape[0])
    keyed = keyed.drop_duplicates(subset=primary_key, keep="first")
    return keyed, metrics
