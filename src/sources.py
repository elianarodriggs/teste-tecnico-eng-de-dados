DATASET_PERIOD = "2016-09-21"
BASE_URL = "https://dadosabertos.c3sl.ufpr.br/curitiba/SIGMU/"

TABLES = [
    {
        "name": "servico_solicitado",
        "file": "2016-09-21_Sigmu_-_SERVICO_SOLICITADO_-_Base_de_Dados.csv",
        "required": True,
        "primary_key": ["SSO_IDF"],
    },
    {
        "name": "situacao_solicitacao",
        "file": "2016-09-21_Sigmu_-_SITUACAO_SOLICITACAO_-_Base_de_Dados.csv",
        "required": True,
        "primary_key": [],
    },
    {
        "name": "servico",
        "file": "2016-09-21_Sigmu_-_SERVICO_-_Base_de_Dados.csv",
        "required": True,
        "primary_key": ["SER_IDF"],
    },
    {
        "name": "servico_executado",
        "file": "2016-09-21_Sigmu_-_SERVICO_EXECUTADO_-_Base_de_Dados.csv",
        "required": True,
        "primary_key": ["SEE_IDF"],
    },
    {
        "name": "gtmbaibaibairro",
        "file": "2016-09-21_Sigmu_-_GTMBAIBAIRRO_-_Base_de_Dados.csv",
        "required": False,
        "primary_key": ["COD_BAIRRO"],
    },
    {
        "name": "tipo_servico",
        "file": "2016-09-21_Sigmu_-_TIPO_SERVICO_-_Base_de_Dados.csv",
        "required": False,
        "primary_key": ["TSE_COD"],
    },
]

DATE_COLUMNS = {
    "servico_solicitado": ["SSO_DATA_SOLICITACAO", "SSO_DATA_REALIZACAO", "SSO_DATA_PREVISTA"],
    "situacao_solicitacao": ["SIS_DATA"],
    "servico": ["SER_DATA_EXECUCAO"],
}

NUMBER_COLUMNS = {
    "servico_solicitado": ["SSO_QTDE_REALIZADA"],
    "servico_executado": [
        "SEE_QUANTIDADE",
        "SEE_VALOR_UNIDADE",
        "SEE_VALOR_TOTAL",
        "SEE_VALOR_UNIDADE_ANTERIOR",
    ],
}
