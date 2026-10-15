from datetime import datetime

import pandas as pd

from sigmu_pipeline.jobs.gold import build_gold


def _frame(rows):
    return pd.DataFrame(rows)


def test_gold_soma_servicos_mantem_solicitacao_sem_execucao_e_nao_entra_orfa():
    solicitacoes = _frame(
        [
            {
                "SSO_IDF": "1",
                "SSO_DATA_SOLICITACAO": datetime(2016, 1, 1, 0, 0),
                "SSO_DATA_REALIZACAO": pd.NaT,
                "SSO_REGIONAL": "UNIDADE REGIONAL BOA VISTA",
                "SSO_ASSUNTO": "PASSEIO",
                "SSO_NOME_BAIRRO": "BOA VISTA",
                "OSO_IDF": "6",
                "SIT_IDF_ATUAL": "23",
            },
            {
                "SSO_IDF": "2",
                "SSO_DATA_SOLICITACAO": datetime(2016, 1, 2, 0, 0),
                "SSO_DATA_REALIZACAO": datetime(2016, 1, 4, 0, 0),
                "SSO_REGIONAL": "UNIDADE REGIONAL BOA VISTA",
                "SSO_ASSUNTO": "ILUMINAÇÃO",
                "SSO_NOME_BAIRRO": "BOA VISTA",
                "OSO_IDF": None,
                "SIT_IDF_ATUAL": "1",
            },
            {
                "SSO_IDF": "3",
                "SSO_DATA_SOLICITACAO": datetime(2016, 6, 1, 0, 0),
                "SSO_DATA_REALIZACAO": pd.NaT,
                "SSO_REGIONAL": None,
                "SSO_ASSUNTO": None,
                "SSO_NOME_BAIRRO": None,
                "OSO_IDF": None,
                "SIT_IDF_ATUAL": "1",
            },
        ]
    )
    servicos = _frame(
        [
            {"SER_IDF": "10", "SSO_IDF": "1", "SER_DATA_EXECUCAO": datetime(2016, 1, 1, 12, 0)},
            {"SER_IDF": "11", "SSO_IDF": "1", "SER_DATA_EXECUCAO": datetime(2016, 1, 3, 0, 0)},
            {"SER_IDF": "99", "SSO_IDF": "999", "SER_DATA_EXECUCAO": datetime(2016, 1, 1)},
        ]
    )
    executados = _frame(
        [
            {"SEE_IDF": "1", "SER_IDF": "10", "SEE_QUANTIDADE": 2, "SEE_VALOR_UNIDADE": 5, "SEE_VALOR_TOTAL": None},
            {"SEE_IDF": "2", "SER_IDF": "11", "SEE_QUANTIDADE": None, "SEE_VALOR_UNIDADE": 3, "SEE_VALOR_TOTAL": 7},
            {"SEE_IDF": "3", "SER_IDF": "11", "SEE_QUANTIDADE": 1, "SEE_VALOR_UNIDADE": 1, "SEE_VALOR_TOTAL": None},
            {"SEE_IDF": "4", "SER_IDF": "50", "SEE_QUANTIDADE": 1, "SEE_VALOR_UNIDADE": 1, "SEE_VALOR_TOTAL": 1},
        ]
    )

    detail, aggregate, quality = build_gold(solicitacoes, servicos, executados)
    by_id = detail.set_index("SSO_IDF")

    assert len(detail) == 3
    assert by_id.loc["1", "qtd_servicos"] == 2
    assert by_id.loc["1", "valor_total_executado"] == 18
    assert by_id.loc["1", "quantidade_total_executada"] == 3
    assert by_id.loc["1", "tempo_atendimento_horas"] == 12
    assert bool(by_id.loc["1", "tem_oso"]) is True
    assert by_id.loc["2", "qtd_servicos"] == 0
    assert by_id.loc["2", "valor_total_executado"] == 0
    assert by_id.loc["2", "tempo_atendimento_horas"] == 48
    assert bool(by_id.loc["2", "tem_oso"]) is False
    assert by_id.loc["3", "regional"] == "NÃO INFORMADO"
    assert pd.isna(by_id.loc["3", "tempo_atendimento_horas"])

    boa_vista = aggregate[
        (aggregate["regional"] == "UNIDADE REGIONAL BOA VISTA") & (aggregate["assunto"] == "PASSEIO")
    ].iloc[0]
    assert boa_vista["volume_solicitacoes"] == 1
    assert boa_vista["valor_total_executado"] == 18
    assert quality.iloc[0]["servicos_sem_solicitacao"] == 1
    assert quality.iloc[0]["itens_sem_servico"] == 1
    assert quality.iloc[0]["solicitacoes_sem_servico"] == 2


def test_tempo_negativo_nao_entra_na_metrica():
    solicitacoes = _frame(
        [
            {
                "SSO_IDF": "7",
                "SSO_DATA_SOLICITACAO": datetime(2016, 5, 1),
                "SSO_DATA_REALIZACAO": datetime(2016, 4, 1),
                "SSO_REGIONAL": "R",
                "SSO_ASSUNTO": "A",
                "SSO_NOME_BAIRRO": "B",
                "OSO_IDF": "1",
                "SIT_IDF_ATUAL": "1",
            }
        ]
    )
    servicos = _frame(
        [{"SER_IDF": "1", "SSO_IDF": "7", "SER_DATA_EXECUCAO": datetime(2007, 7, 2)}]
    )
    executados = _frame(
        [
            {
                "SEE_IDF": "1",
                "SER_IDF": "1",
                "SEE_QUANTIDADE": None,
                "SEE_VALOR_UNIDADE": 2.03,
                "SEE_VALOR_TOTAL": None,
            }
        ]
    )

    detail, _, quality = build_gold(solicitacoes, servicos, executados)
    row = detail.iloc[0]
    assert pd.isna(row["tempo_atendimento_horas"])
    assert bool(row["tempo_negativo"]) is True
    assert row["valor_total_executado"] == 0
    assert quality.iloc[0]["itens_sem_valor_no_fato"] == 1
