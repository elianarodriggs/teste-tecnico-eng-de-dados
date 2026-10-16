from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import pandas as pd

from sources import DATASET_PERIOD, TABLES
from storage import extraction_date, manifest, put_json, put_parquet, read_parquet

logger = logging.getLogger(__name__)

SQL_PATH = Path(__file__).resolve().parents[1] / "sql" / "gold.sql"


def _label(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.replace(r"\s+", " ", regex=True).str.strip().str.upper()
    return text.mask(text.isna() | (text == ""), "NÃO INFORMADO")


def build_analytics(
    solicitacoes: pd.DataFrame,
    servicos: pd.DataFrame,
    executados: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    sso = solicitacoes.copy()
    ser = servicos.copy()
    see = executados.copy()
    for frame, column in (
        (sso, "SSO_IDF"),
        (ser, "SSO_IDF"),
        (ser, "SER_IDF"),
        (see, "SER_IDF"),
        (see, "SEE_IDF"),
    ):
        frame[column] = frame[column].astype("string").str.strip()
        frame.loc[frame[column].isin(["", "<NA>", "nan", "None"]), column] = pd.NA

    sso["regional"] = _label(sso["SSO_REGIONAL"])
    sso["assunto"] = _label(sso["SSO_ASSUNTO"])

    connection = duckdb.connect()
    connection.register("servico_solicitado", sso)
    connection.register("servico", ser)
    connection.register("servico_executado", see)
    connection.execute(SQL_PATH.read_text(encoding="utf-8"))
    fato = connection.execute("SELECT * FROM fato").df()
    agregado = connection.execute("SELECT * FROM agregado").df()

    orphans_service = int((~ser["SSO_IDF"].isin(set(sso["SSO_IDF"].dropna()))).sum())
    orphans_item = int((~see["SER_IDF"].isin(set(ser["SER_IDF"].dropna()))).sum())
    checks = {
        "solicitacoes_silver": int(sso["SSO_IDF"].nunique(dropna=True)),
        "solicitacoes_gold": int(fato["SSO_IDF"].nunique(dropna=True)),
        "linhas_gold": int(len(fato)),
        "solicitacoes_sem_execucao": int((fato["possui_execucao"] == 0).sum()),
        "tempos_negativos": int(fato["tempo_negativo"].sum()),
        "tempos_validos": int(fato["tempo_horas"].notna().sum()),
        "servicos_sem_solicitacao": orphans_service,
        "itens_sem_servico": orphans_item,
        "valor_executado": None if fato["valor_executado"].isna().all() else float(fato["valor_executado"].sum()),
    }
    if checks["linhas_gold"] != checks["solicitacoes_silver"]:
        raise RuntimeError(
            "a Gold mudou a contagem de solicitações: "
            f"{checks['solicitacoes_silver']} na Silver, {checks['linhas_gold']} na Gold"
        )
    if checks["solicitacoes_gold"] != checks["linhas_gold"]:
        raise RuntimeError("o join duplicou solicitações na Gold")
    return fato, agregado, checks


def run_gold() -> dict:
    when = extraction_date()
    solicitacoes = read_parquet(f"silver/servico_solicitado/extraction_date={when}/data.parquet")
    servicos = read_parquet(f"silver/servico/extraction_date={when}/data.parquet")
    executados = read_parquet(f"silver/servico_executado/extraction_date={when}/data.parquet")
    fato, agregado, checks = build_analytics(solicitacoes, servicos, executados)

    fato_key = f"gold/fato_solicitacao/extraction_date={when}/data.parquet"
    agg_key = f"gold/agregado_regional_assunto/extraction_date={when}/data.parquet"
    put_parquet(fato_key, fato)
    put_parquet(agg_key, agregado)
    put_parquet(f"gold/validacao/extraction_date={when}/data.parquet", pd.DataFrame([checks]))
    for name, key, rows in (
        ("fato_solicitacao", fato_key, len(fato)),
        ("agregado_regional_assunto", agg_key, len(agregado)),
    ):
        put_json(
            key.rsplit("/", 1)[0] + "/_manifest.json",
            manifest(
                layer="gold",
                table=name,
                extraction_date=when,
                dataset_period=DATASET_PERIOD,
                object_key=key,
                rows=rows,
                grain="SSO_IDF" if name == "fato_solicitacao" else "regional,assunto",
            ),
        )
    logger.info("gold %s", checks)
    return {"extraction_date": when, "checks": checks, "agregado_rows": len(agregado), "tables_used": [t["name"] for t in TABLES]}
