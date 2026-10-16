PERIODO = "2016-09-21"
URL_BASE = "https://dadosabertos.c3sl.ufpr.br/curitiba/SIGMU/"

TABELAS = [
    {
        "nome": "servico_solicitado",
        "arquivo": "2016-09-21_Sigmu_-_SERVICO_SOLICITADO_-_Base_de_Dados.csv",
        "obrigatoria": True,
        "chave": ["SSO_IDF"],
    },
    {
        "nome": "situacao_solicitacao",
        "arquivo": "2016-09-21_Sigmu_-_SITUACAO_SOLICITACAO_-_Base_de_Dados.csv",
        "obrigatoria": True,
        "chave": [],
    },
    {
        "nome": "servico",
        "arquivo": "2016-09-21_Sigmu_-_SERVICO_-_Base_de_Dados.csv",
        "obrigatoria": True,
        "chave": ["SER_IDF"],
    },
    {
        "nome": "servico_executado",
        "arquivo": "2016-09-21_Sigmu_-_SERVICO_EXECUTADO_-_Base_de_Dados.csv",
        "obrigatoria": True,
        "chave": ["SEE_IDF"],
    },
    {
        "nome": "gtmbaibaibairro",
        "arquivo": "2016-09-21_Sigmu_-_GTMBAIBAIRRO_-_Base_de_Dados.csv",
        "obrigatoria": False,
        "chave": ["COD_BAIRRO"],
    },
    {
        "nome": "tipo_servico",
        "arquivo": "2016-09-21_Sigmu_-_TIPO_SERVICO_-_Base_de_Dados.csv",
        "obrigatoria": False,
        "chave": ["TSE_COD"],
    },
]

COLUNAS_DATA = {
    "servico_solicitado": ["SSO_DATA_SOLICITACAO", "SSO_DATA_REALIZACAO", "SSO_DATA_PREVISTA"],
    "situacao_solicitacao": ["SIS_DATA"],
    "servico": ["SER_DATA_EXECUCAO"],
}

COLUNAS_NUMERO = {
    "servico_solicitado": ["SSO_QTDE_REALIZADA"],
    "servico_executado": [
        "SEE_QUANTIDADE",
        "SEE_VALOR_UNIDADE",
        "SEE_VALOR_TOTAL",
        "SEE_VALOR_UNIDADE_ANTERIOR",
    ],
}
