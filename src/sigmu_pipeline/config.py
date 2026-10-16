from __future__ import annotations

import os
from dataclasses import dataclass

SNAPSHOT_DATE = "2016-09-21"
BASE_URL = "https://dadosabertos.c3sl.ufpr.br/curitiba/SIGMU/"

# Nome lógico, arquivo no espelho C3SL e chave natural.
# primary_key vazio mantém o histórico inteiro (situacao_solicitacao).
TABLES = {
    "servico_solicitado": {
        "file": "2016-09-21_Sigmu_-_SERVICO_SOLICITADO_-_Base_de_Dados.csv",
        "primary_key": ["SSO_IDF"],
    },
    "situacao_solicitacao": {
        "file": "2016-09-21_Sigmu_-_SITUACAO_SOLICITACAO_-_Base_de_Dados.csv",
        "primary_key": [],
    },
    "servico": {
        "file": "2016-09-21_Sigmu_-_SERVICO_-_Base_de_Dados.csv",
        "primary_key": ["SER_IDF"],
    },
    "servico_executado": {
        "file": "2016-09-21_Sigmu_-_SERVICO_EXECUTADO_-_Base_de_Dados.csv",
        "primary_key": ["SEE_IDF"],
    },
    "gtmbaibaibairro": {
        "file": "2016-09-21_Sigmu_-_GTMBAIBAIRRO_-_Base_de_Dados.csv",
        "primary_key": ["COD_BAIRRO"],
    },
    "tipo_servico": {
        "file": "2016-09-21_Sigmu_-_TIPO_SERVICO_-_Base_de_Dados.csv",
        "primary_key": ["TSE_COD"],
    },
}


@dataclass(frozen=True)
class S3Config:
    endpoint_url: str
    access_key: str
    secret_key: str
    bucket: str


@dataclass(frozen=True)
class PipelineConfig:
    s3: S3Config
    snapshot_date: str
    base_url: str
    tables: dict


def load_config() -> PipelineConfig:
    return PipelineConfig(
        s3=S3Config(
            endpoint_url=os.environ.get("S3_ENDPOINT", "http://localhost:8333"),
            access_key=os.environ.get("S3_ACCESS_KEY", "admin"),
            secret_key=os.environ.get("S3_SECRET_KEY", "change-me"),
            bucket=os.environ.get("S3_BUCKET", "lake"),
        ),
        snapshot_date=SNAPSHOT_DATE,
        base_url=BASE_URL,
        tables=TABLES,
    )


def object_prefix(layer: str, table: str, snapshot_date: str) -> str:
    return f"{layer}/{table}/snapshot_date={snapshot_date}"
