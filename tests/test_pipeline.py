from datetime import datetime

import pandas as pd

from leitor import LeitorCsv
from pipeline import Pipeline


def test_mascara_e_linha_irrecuperavel_vao_para_quarentena():
    raw = (
        "SSO_IDF;SSO_ASSUNTO\n"
        "-------;-----------\n"
        "1;PASSEIO\n"
        "2;TEXTO;COM;DELIMITADOR\n"
        "3;DRENAGEM\n"
    ).encode("latin-1")
    frame, quarantine, info = LeitorCsv().ler(raw)
    assert info["mascara_ignorada"] is True
    assert list(frame["SSO_IDF"]) == ["1", "3"]
    assert quarantine.iloc[0]["reason"] == "contagem_de_campos"


def test_gold_nao_multiplica_solicitacao_e_mantem_quem_nao_tem_execucao():
    solicitacoes = pd.DataFrame(
        [
            {
                "SSO_IDF": "1",
                "SSO_DATA_SOLICITACAO": datetime(2016, 1, 1),
                "SSO_DATA_REALIZACAO": pd.NaT,
                "SSO_REGIONAL": "Unidade Regional Boa Vista",
                "SSO_ASSUNTO": "PASSEIO",
                "OSO_IDF": "6",
                "SIT_IDF_ATUAL": "23",
            },
            {
                "SSO_IDF": "2",
                "SSO_DATA_SOLICITACAO": datetime(2016, 1, 2),
                "SSO_DATA_REALIZACAO": datetime(2016, 1, 4),
                "SSO_REGIONAL": "UNIDADE REGIONAL BOA VISTA",
                "SSO_ASSUNTO": None,
                "OSO_IDF": None,
                "SIT_IDF_ATUAL": "1",
            },
        ]
    )
    servicos = pd.DataFrame(
        [
            {"SER_IDF": "10", "SSO_IDF": "1", "SER_DATA_EXECUCAO": datetime(2016, 1, 1, 12)},
            {"SER_IDF": "11", "SSO_IDF": "1", "SER_DATA_EXECUCAO": datetime(2016, 1, 3)},
            {"SER_IDF": "99", "SSO_IDF": "999", "SER_DATA_EXECUCAO": datetime(2016, 1, 1)},
        ]
    )
    executados = pd.DataFrame(
        [
            {"SEE_IDF": "1", "SER_IDF": "10", "SEE_QUANTIDADE": 2.0, "SEE_VALOR_UNIDADE": 5.0, "SEE_VALOR_TOTAL": None},
            {"SEE_IDF": "2", "SER_IDF": "11", "SEE_QUANTIDADE": None, "SEE_VALOR_UNIDADE": 3.0, "SEE_VALOR_TOTAL": 7.0},
            {"SEE_IDF": "3", "SER_IDF": "11", "SEE_QUANTIDADE": 1.0, "SEE_VALOR_UNIDADE": 1.0, "SEE_VALOR_TOTAL": None},
            {"SEE_IDF": "4", "SER_IDF": "50", "SEE_QUANTIDADE": 1.0, "SEE_VALOR_UNIDADE": 1.0, "SEE_VALOR_TOTAL": 1.0},
        ]
    )

    fato, agregado, checks = Pipeline().montar(solicitacoes, servicos, executados)
    assert len(fato) == 2
    assert checks["solicitacoes_gold"] == 2
    boa = fato.set_index("SSO_IDF").loc["1"]
    assert boa["qtd_servicos"] == 2
    assert boa["valor_executado"] == 18
    assert boa["quantidade_executada"] == 3
    assert boa["tempo_horas"] == 12
    assert fato.set_index("SSO_IDF").loc["2"]["possui_execucao"] == 0
    assert pd.isna(fato.set_index("SSO_IDF").loc["2"]["valor_executado"])
    assert checks["servicos_sem_solicitacao"] == 1
    assert checks["itens_sem_servico"] == 1
    assert agregado["regional"].nunique() == 1


def test_tempo_negativo_nao_entra_na_metrica():
    solicitacoes = pd.DataFrame(
        [
            {
                "SSO_IDF": "7",
                "SSO_DATA_SOLICITACAO": datetime(2016, 5, 1),
                "SSO_DATA_REALIZACAO": datetime(2016, 4, 1),
                "SSO_REGIONAL": "R",
                "SSO_ASSUNTO": "A",
                "OSO_IDF": "1",
                "SIT_IDF_ATUAL": "1",
            }
        ]
    )
    servicos = pd.DataFrame(
        [{"SER_IDF": "1", "SSO_IDF": "7", "SER_DATA_EXECUCAO": datetime(2007, 7, 2)}]
    )
    executados = pd.DataFrame(
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
    fato, _, checks = Pipeline().montar(solicitacoes, servicos, executados)
    assert pd.isna(fato.iloc[0]["tempo_horas"])
    assert fato.iloc[0]["tempo_negativo"] == 1
    assert pd.isna(fato.iloc[0]["valor_executado"])
    assert checks["tempos_negativos"] == 1
