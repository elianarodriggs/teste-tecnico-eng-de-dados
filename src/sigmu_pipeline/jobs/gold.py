from __future__ import annotations

import logging

import pandas as pd

from sigmu_pipeline.config import PipelineConfig, object_prefix
from sigmu_pipeline.io import lineage_manifest, put_bytes, put_json, read_parquet, write_parquet
from sigmu_pipeline.quality import hours_between

logger = logging.getLogger(__name__)

NAO_INFORMADO = "NÃO INFORMADO"


def _rotulo(series: pd.Series) -> pd.Series:
    """Uniformiza rótulo analítico: espaço, caixa e vazio.

    O extrato repete a mesma regional em caixa alta e em caixa título.
    Sem isso o ranking de região parte volume e valor em duas linhas.
    """
    text = series.astype("string").str.replace(r"\s+", " ", regex=True).str.strip().str.upper()
    return text.fillna(NAO_INFORMADO).replace("", NAO_INFORMADO)


def _item_value(see: pd.DataFrame) -> pd.Series:
    total = pd.to_numeric(see["SEE_VALOR_TOTAL"], errors="coerce")
    quantity = pd.to_numeric(see["SEE_QUANTIDADE"], errors="coerce")
    unit = pd.to_numeric(see["SEE_VALOR_UNIDADE"], errors="coerce")
    return total.fillna(quantity * unit)


def build_gold(
    solicitacoes: pd.DataFrame,
    servicos: pd.DataFrame,
    executados: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fato no grão da solicitação e agregado regional × assunto.

    Várias linhas de serviço na mesma solicitação são somadas.
    Solicitação sem execução permanece no fato, com tempo nulo.
    """
    sso = solicitacoes.copy()
    ser = servicos.copy()
    see = executados.copy()

    for frame, column in ((sso, "SSO_IDF"), (ser, "SSO_IDF"), (ser, "SER_IDF"), (see, "SER_IDF"), (see, "SEE_IDF")):
        frame[column] = frame[column].astype("string").str.strip()
        frame.loc[frame[column].isin(["", "<NA>", "nan", "None"]), column] = pd.NA

    see = see.copy()
    see["valor_item"] = _item_value(see)
    see["quantidade_item"] = pd.to_numeric(see["SEE_QUANTIDADE"], errors="coerce")

    sso_ids = set(sso["SSO_IDF"].dropna())
    ser_ids = set(ser["SER_IDF"].dropna())
    servicos_sem_solicitacao = int((~ser["SSO_IDF"].isin(sso_ids)).sum())
    itens_sem_servico = int((~see["SER_IDF"].isin(ser_ids)).sum())

    ser_linked = ser[ser["SSO_IDF"].notna() & ser["SSO_IDF"].isin(sso_ids)]
    ser_agg = (
        ser_linked.groupby("SSO_IDF", dropna=True)
        .agg(
            qtd_servicos=("SER_IDF", "nunique"),
            data_primeira_execucao=("SER_DATA_EXECUCAO", "min"),
            data_ultima_execucao=("SER_DATA_EXECUCAO", "max"),
        )
        .reset_index()
    )

    ser_chave = ser.drop_duplicates(subset=["SER_IDF"], keep="first")
    see_via_ser = see.merge(ser_chave[["SER_IDF", "SSO_IDF"]], on="SER_IDF", how="left")
    itens_sem_solicitacao = int((~see_via_ser["SSO_IDF"].isin(sso_ids)).sum())
    see_no_fato = see_via_ser[see_via_ser["SSO_IDF"].isin(sso_ids)].copy()
    see_no_fato["sem_valor"] = see_no_fato["valor_item"].isna().astype(int)
    see_agg = (
        see_no_fato.groupby("SSO_IDF", dropna=True)
        .agg(
            qtd_itens_executados=("SEE_IDF", "count"),
            quantidade_total_executada=("quantidade_item", "sum"),
            valor_total_executado=("valor_item", "sum"),
            itens_sem_valor=("sem_valor", "sum"),
        )
        .reset_index()
    )

    detail = sso.merge(ser_agg, on="SSO_IDF", how="left").merge(see_agg, on="SSO_IDF", how="left")
    detail["qtd_servicos"] = detail["qtd_servicos"].fillna(0).astype(int)
    detail["qtd_itens_executados"] = detail["qtd_itens_executados"].fillna(0).astype(int)
    detail["quantidade_total_executada"] = detail["quantidade_total_executada"].fillna(0.0)
    detail["valor_total_executado"] = detail["valor_total_executado"].fillna(0.0)
    detail["itens_sem_valor"] = detail["itens_sem_valor"].fillna(0).astype(int)

    detail["regional"] = _rotulo(detail["SSO_REGIONAL"])
    detail["assunto"] = _rotulo(detail["SSO_ASSUNTO"])
    detail["bairro"] = _rotulo(detail["SSO_NOME_BAIRRO"])

    oso = detail["OSO_IDF"].astype("string").str.strip()
    detail["tem_oso"] = oso.notna() & ~oso.isin(["", "<NA>", "nan", "None"])
    detail["tem_servico"] = detail["qtd_servicos"] > 0

    horas_execucao = hours_between(detail["SSO_DATA_SOLICITACAO"], detail["data_primeira_execucao"])
    tem_data_execucao = detail["data_primeira_execucao"].notna()
    execucao_anterior = tem_data_execucao & (detail["data_primeira_execucao"] < detail["SSO_DATA_SOLICITACAO"])
    detail["tempo_atendimento_horas"] = horas_execucao
    fallback = hours_between(detail["SSO_DATA_SOLICITACAO"], detail["SSO_DATA_REALIZACAO"])
    usar_fallback = detail["tempo_atendimento_horas"].isna() & ~tem_data_execucao
    detail.loc[usar_fallback, "tempo_atendimento_horas"] = fallback.loc[usar_fallback]
    realizacao_anterior = (
        usar_fallback
        & detail["SSO_DATA_REALIZACAO"].notna()
        & (detail["SSO_DATA_REALIZACAO"] < detail["SSO_DATA_SOLICITACAO"])
    )
    detail["tempo_negativo"] = (execucao_anterior | realizacao_anterior).fillna(False)

    detail["tem_execucao_registrada"] = tem_data_execucao | detail["SSO_DATA_REALIZACAO"].notna()

    fact_columns = [
        "SSO_IDF",
        "SSO_DATA_SOLICITACAO",
        "SSO_DATA_REALIZACAO",
        "data_primeira_execucao",
        "data_ultima_execucao",
        "regional",
        "assunto",
        "bairro",
        "OSO_IDF",
        "SIT_IDF_ATUAL",
        "tem_oso",
        "tem_servico",
        "tem_execucao_registrada",
        "tempo_negativo",
        "tempo_atendimento_horas",
        "qtd_servicos",
        "qtd_itens_executados",
        "quantidade_total_executada",
        "valor_total_executado",
        "itens_sem_valor",
    ]
    detail = detail[fact_columns]

    grouped = detail.groupby(["regional", "assunto"], dropna=False)
    aggregate = grouped.agg(
        volume_solicitacoes=("SSO_IDF", "count"),
        solicitacoes_com_oso=("tem_oso", "sum"),
        solicitacoes_com_execucao=("tem_execucao_registrada", "sum"),
        solicitacoes_com_servico=("tem_servico", "sum"),
        tempo_amostras=("tempo_atendimento_horas", "count"),
        tempo_medio_horas=("tempo_atendimento_horas", "mean"),
        tempo_mediano_horas=("tempo_atendimento_horas", "median"),
        quantidade_total_executada=("quantidade_total_executada", "sum"),
        valor_total_executado=("valor_total_executado", "sum"),
    ).reset_index()
    aggregate["solicitacoes_com_oso"] = aggregate["solicitacoes_com_oso"].astype(int)
    aggregate["solicitacoes_com_execucao"] = aggregate["solicitacoes_com_execucao"].astype(int)
    aggregate["solicitacoes_com_servico"] = aggregate["solicitacoes_com_servico"].astype(int)
    aggregate["pct_sem_oso"] = 1 - (aggregate["solicitacoes_com_oso"] / aggregate["volume_solicitacoes"])
    aggregate["pct_sem_execucao"] = 1 - (
        aggregate["solicitacoes_com_execucao"] / aggregate["volume_solicitacoes"]
    )
    aggregate = aggregate.sort_values(
        ["volume_solicitacoes", "valor_total_executado"],
        ascending=False,
    ).reset_index(drop=True)

    quality = pd.DataFrame(
        [
            {
                "solicitacoes": int(len(detail)),
                "servicos": int(len(ser)),
                "itens_executados": int(len(see)),
                "servicos_sem_solicitacao": servicos_sem_solicitacao,
                "itens_sem_servico": itens_sem_servico,
                "itens_sem_solicitacao": itens_sem_solicitacao,
                "solicitacoes_sem_servico": int((~detail["tem_servico"]).sum()),
                "solicitacoes_sem_execucao": int((~detail["tem_execucao_registrada"]).sum()),
                "solicitacoes_sem_oso": int((~detail["tem_oso"]).sum()),
                "tempos_negativos": int(detail["tempo_negativo"].sum()),
                "itens_sem_valor_no_fato": int(detail["itens_sem_valor"].sum()),
                "valor_total_executado": float(detail["valor_total_executado"].sum()),
                "quantidade_total_executada": float(detail["quantidade_total_executada"].sum()),
            }
        ]
    )
    return detail, aggregate, quality


def _publish(cfg: PipelineConfig, name: str, frame: pd.DataFrame, extra: dict) -> str:
    prefix = object_prefix("gold", name, cfg.snapshot_date)
    data_key = f"{prefix}/data.parquet"
    write_parquet(cfg.s3, data_key, frame)
    put_json(
        cfg.s3,
        f"{prefix}/_manifest.json",
        lineage_manifest(
            layer="gold",
            table=name,
            snapshot_date=cfg.snapshot_date,
            object_key=data_key,
            rows=len(frame),
            **extra,
        ),
    )
    put_bytes(cfg.s3, f"{prefix}/_SUCCESS", b"", "text/plain")
    return data_key


def run_gold(cfg: PipelineConfig) -> dict:
    snapshot = cfg.snapshot_date
    solicitacoes = read_parquet(cfg.s3, f"{object_prefix('silver', 'servico_solicitado', snapshot)}/data.parquet")
    servicos = read_parquet(cfg.s3, f"{object_prefix('silver', 'servico', snapshot)}/data.parquet")
    executados = read_parquet(cfg.s3, f"{object_prefix('silver', 'servico_executado', snapshot)}/data.parquet")

    detail, aggregate, quality = build_gold(solicitacoes, servicos, executados)
    keys = {
        "fato_solicitacao_execucao": _publish(
            cfg,
            "fato_solicitacao_execucao",
            detail,
            {"grain": "SSO_IDF"},
        ),
        "agregado_regional_assunto": _publish(
            cfg,
            "agregado_regional_assunto",
            aggregate,
            {"grain": "regional,assunto"},
        ),
        "qualidade_integracao": _publish(
            cfg,
            "qualidade_integracao",
            quality,
            {"grain": "snapshot"},
        ),
    }
    summary = {"snapshot_date": snapshot, "keys": keys, "quality": quality.iloc[0].to_dict()}
    logger.info("gold %s", summary["quality"])
    return summary
