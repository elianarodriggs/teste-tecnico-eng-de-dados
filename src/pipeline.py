import hashlib
import logging
import time
from pathlib import Path

import duckdb
import pandas as pd
import requests

from configuracao import PERIODO, TABELAS, URL_BASE
from lago import Lago
from leitor import LeitorCsv

SQL_GOLD = Path(__file__).resolve().parents[1] / "sql" / "gold.sql"


class Pipeline:
    def __init__(self):
        self.lago = Lago()
        self.leitor = LeitorCsv()

    def baixar(self, url):
        ultimo_erro = None
        for tentativa in range(1, 4):
            try:
                resposta = requests.get(url, timeout=60)
                resposta.raise_for_status()
                if not resposta.content:
                    raise RuntimeError(f"arquivo vazio: {url}")
                return resposta.content
            except Exception as erro:
                ultimo_erro = erro
                logging.warning("falha ao baixar %s (%s); tentativa %s/3", url, erro, tentativa)
                time.sleep(2)
        raise RuntimeError(f"não foi possível baixar {url}") from ultimo_erro

    def executar_ou_pular(self, tabela, acao):
        try:
            return acao()
        except Exception:
            if tabela["obrigatoria"]:
                raise
            logging.exception("fonte opcional indisponível: %s", tabela["nome"])
            return None

    def bronze(self):
        self.lago.garantir_bucket()
        quando = self.lago.data_extracao
        resumo = {"data_extracao": quando, "periodo": PERIODO, "tabelas": {}}

        for tabela in TABELAS:
            url = URL_BASE + tabela["arquivo"]
            logging.info("bronze %s <- %s", tabela["nome"], url)
            conteudo = self.executar_ou_pular(tabela, lambda url=url: self.baixar(url))
            if conteudo is None:
                resumo["tabelas"][tabela["nome"]] = {"status": "falha_opcional"}
                continue

            caminho = f"bronze/{tabela['nome']}/extraction_date={quando}/{tabela['arquivo']}"
            self.lago.gravar(caminho, conteudo, "text/csv")
            resumo_arquivo = self.lago.manifesto(
                camada="bronze",
                tabela=tabela["nome"],
                url=url,
                arquivo=tabela["arquivo"],
                data_extracao=quando,
                periodo=PERIODO,
                bytes=len(conteudo),
                sha256=hashlib.sha256(conteudo).hexdigest(),
                caminho=caminho,
                obrigatoria=tabela["obrigatoria"],
            )
            self.lago.gravar_json(f"bronze/{tabela['nome']}/extraction_date={quando}/_manifest.json", resumo_arquivo)
            resumo["tabelas"][tabela["nome"]] = {
                "bytes": len(conteudo),
                "caminho": caminho,
                "sha256": resumo_arquivo["sha256"],
            }

        return resumo

    def silver(self):
        quando = self.lago.data_extracao
        metricas = []
        quarentenas = []

        for tabela in TABELAS:
            caminho_bronze = f"bronze/{tabela['nome']}/extraction_date={quando}/{tabela['arquivo']}"
            logging.info("silver %s <- %s", tabela["nome"], caminho_bronze)
            bruto = self.executar_ou_pular(tabela, lambda caminho=caminho_bronze: self.lago.ler(caminho))
            if bruto is None:
                continue

            quadro, quarentena, info = self.leitor.ler(bruto)
            lidas = len(quadro) + len(quarentena)
            quadro, tipos = self.leitor.tipar(tabela["nome"], quadro)

            sem_chave = pd.DataFrame()
            if tabela["chave"]:
                faltando = quadro[tabela["chave"]].isna().any(axis=1)
                if faltando.any():
                    sem_chave = quadro.loc[faltando].copy()
                    sem_chave.insert(0, "reason", "chave_nula")
                    sem_chave.insert(0, "table", tabela["nome"])
            quadro, duplicatas = self.leitor.deduplicar(quadro, tabela["chave"])

            caminho = f"silver/{tabela['nome']}/extraction_date={quando}/data.parquet"
            self.lago.gravar_parquet(caminho, quadro)
            if not quarentena.empty:
                quarentena.insert(0, "table", tabela["nome"])
                quarentenas.append(quarentena)
            if not sem_chave.empty:
                quarentenas.append(sem_chave)

            linha = {
                "tabela": tabela["nome"],
                "linhas_entrada": lidas,
                "linhas_saida": len(quadro),
                "linhas_rejeitadas": len(quarentena),
                "chaves_nulas": duplicatas["chaves_nulas"],
                "duplicatas_exatas": duplicatas["duplicatas_exatas"],
                "duplicatas_divergentes": duplicatas["duplicatas_divergentes"],
                "bytes_nulos": info["bytes_nulos"],
                "datas_invalidas": tipos["datas_invalidas"],
                "numeros_invalidos": tipos["numeros_invalidos"],
            }
            metricas.append(linha)
            self.lago.gravar_json(
                f"silver/{tabela['nome']}/extraction_date={quando}/_manifest.json",
                self.lago.manifesto(
                    camada="silver",
                    data_extracao=quando,
                    periodo=PERIODO,
                    origem=caminho_bronze,
                    caminho=caminho,
                    **linha,
                ),
            )
            logging.info("silver %s: %s linhas", tabela["nome"], len(quadro))

        prefixo = f"silver/_quality/extraction_date={quando}"
        self.lago.gravar_parquet(f"{prefixo}/metrics.parquet", pd.DataFrame(metricas))
        if quarentenas:
            rejeitadas = pd.concat(quarentenas, ignore_index=True)
        else:
            rejeitadas = pd.DataFrame(columns=["table", "line_number", "reason", "raw_line"])
        self.lago.gravar_parquet(f"{prefixo}/quarentena.parquet", rejeitadas)
        return {"data_extracao": quando, "tabelas": metricas, "linhas_rejeitadas": len(rejeitadas)}

    def montar(self, pedidos, servicos, itens):
        pedidos = pedidos.copy()
        servicos = servicos.copy()
        itens = itens.copy()
        for quadro, coluna in (
            (pedidos, "SSO_IDF"),
            (servicos, "SSO_IDF"),
            (servicos, "SER_IDF"),
            (itens, "SER_IDF"),
            (itens, "SEE_IDF"),
        ):
            quadro[coluna] = quadro[coluna].astype("string").str.strip()
            quadro.loc[quadro[coluna].isin(["", "<NA>", "nan", "None"]), coluna] = pd.NA

        for origem, destino in (("SSO_REGIONAL", "regional"), ("SSO_ASSUNTO", "assunto")):
            texto = pedidos[origem].astype("string").str.replace(r"\s+", " ", regex=True).str.strip().str.upper()
            pedidos[destino] = texto.mask(texto.isna() | (texto == ""), "NÃO INFORMADO")

        conexao = duckdb.connect()
        conexao.register("servico_solicitado", pedidos)
        conexao.register("servico", servicos)
        conexao.register("servico_executado", itens)
        conexao.execute(SQL_GOLD.read_text(encoding="utf-8"))
        fato = conexao.execute("SELECT * FROM fato").df()
        agregado = conexao.execute("SELECT * FROM agregado").df()

        checagens = {
            "solicitacoes_silver": int(pedidos["SSO_IDF"].nunique(dropna=True)),
            "solicitacoes_gold": int(fato["SSO_IDF"].nunique(dropna=True)),
            "linhas_gold": int(len(fato)),
            "solicitacoes_sem_execucao": int((fato["possui_execucao"] == 0).sum()),
            "tempos_negativos": int(fato["tempo_negativo"].sum()),
            "tempos_validos": int(fato["tempo_horas"].notna().sum()),
            "servicos_sem_solicitacao": int((~servicos["SSO_IDF"].isin(set(pedidos["SSO_IDF"].dropna()))).sum()),
            "itens_sem_servico": int((~itens["SER_IDF"].isin(set(servicos["SER_IDF"].dropna()))).sum()),
            "valor_executado": None if fato["valor_executado"].isna().all() else float(fato["valor_executado"].sum()),
        }
        if checagens["linhas_gold"] != checagens["solicitacoes_silver"]:
            raise RuntimeError(
                "a Gold mudou a contagem de solicitações: "
                f"{checagens['solicitacoes_silver']} na Silver, {checagens['linhas_gold']} na Gold"
            )
        if checagens["solicitacoes_gold"] != checagens["linhas_gold"]:
            raise RuntimeError("o join duplicou solicitações na Gold")
        return fato, agregado, checagens

    def gold(self):
        quando = self.lago.data_extracao
        pedidos = self.lago.ler_parquet(f"silver/servico_solicitado/extraction_date={quando}/data.parquet")
        servicos = self.lago.ler_parquet(f"silver/servico/extraction_date={quando}/data.parquet")
        itens = self.lago.ler_parquet(f"silver/servico_executado/extraction_date={quando}/data.parquet")
        fato, agregado, checagens = self.montar(pedidos, servicos, itens)

        caminho_fato = f"gold/fato_solicitacao/extraction_date={quando}/data.parquet"
        caminho_agregado = f"gold/agregado_regional_assunto/extraction_date={quando}/data.parquet"
        self.lago.gravar_parquet(caminho_fato, fato)
        self.lago.gravar_parquet(caminho_agregado, agregado)
        self.lago.gravar_parquet(f"gold/validacao/extraction_date={quando}/data.parquet", pd.DataFrame([checagens]))
        self.lago.gravar_json(
            f"gold/fato_solicitacao/extraction_date={quando}/_manifest.json",
            self.lago.manifesto(
                camada="gold",
                tabela="fato_solicitacao",
                data_extracao=quando,
                periodo=PERIODO,
                caminho=caminho_fato,
                linhas=len(fato),
                grao="SSO_IDF",
            ),
        )
        self.lago.gravar_json(
            f"gold/agregado_regional_assunto/extraction_date={quando}/_manifest.json",
            self.lago.manifesto(
                camada="gold",
                tabela="agregado_regional_assunto",
                data_extracao=quando,
                periodo=PERIODO,
                caminho=caminho_agregado,
                linhas=len(agregado),
                grao="regional,assunto",
            ),
        )
        logging.info("gold %s", checagens)
        return {
            "data_extracao": quando,
            "checagens": checagens,
            "linhas_agregado": len(agregado),
            "tabelas": [tabela["nome"] for tabela in TABELAS],
        }
