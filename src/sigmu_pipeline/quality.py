from __future__ import annotations

import pandas as pd

DATE_COLUMNS = {
    "servico_solicitado": ["SSO_DATA_SOLICITACAO", "SSO_DATA_REALIZACAO", "SSO_DATA_PREVISTA"],
    "situacao_solicitacao": ["SIS_DATA"],
    "servico": ["SER_DATA_EXECUCAO"],
}

FLOAT_COLUMNS = {
    "servico_solicitado": ["SSO_QTDE_REALIZADA"],
    "servico_executado": [
        "SEE_QUANTIDADE",
        "SEE_VALOR_UNIDADE",
        "SEE_VALOR_TOTAL",
        "SEE_VALOR_UNIDADE_ANTERIOR",
    ],
}


def blank_to_null(frame: pd.DataFrame) -> pd.DataFrame:
    cleaned = frame.copy()
    for column in cleaned.columns:
        if cleaned[column].dtype == object or str(cleaned[column].dtype) == "string":
            as_text = cleaned[column].astype("string").str.strip()
            cleaned[column] = as_text.mask(as_text == "", pd.NA)
    return cleaned


def apply_types(table: str, frame: pd.DataFrame) -> pd.DataFrame:
    typed = blank_to_null(frame)
    for column in DATE_COLUMNS.get(table, []):
        if column in typed.columns:
            typed[column] = pd.to_datetime(typed[column], errors="coerce")
    for column in FLOAT_COLUMNS.get(table, []):
        if column in typed.columns:
            as_text = typed[column].astype("string").str.replace(",", ".", regex=False)
            typed[column] = pd.to_numeric(as_text, errors="coerce")
    return typed


def deduplicate(frame: pd.DataFrame, primary_key: list[str]) -> tuple[pd.DataFrame, int, int]:
    if not primary_key or any(column not in frame.columns for column in primary_key):
        return frame, 0, 0
    before = len(frame)
    without_null_key = frame.dropna(subset=primary_key)
    null_keys = before - len(without_null_key)
    deduped = without_null_key.drop_duplicates(subset=primary_key, keep="first")
    duplicates = len(without_null_key) - len(deduped)
    return deduped, null_keys, duplicates


def hours_between(start: pd.Series, end: pd.Series) -> pd.Series:
    delta = (end - start).dt.total_seconds() / 3600.0
    return delta.where(delta >= 0)
