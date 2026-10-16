import pandas as pd

from configuracao import COLUNAS_DATA, COLUNAS_NUMERO

DELIMITADOR = ";"


class LeitorCsv:
    def ler(self, bruto):
        bytes_nulos = bruto.count(b"\x00")
        texto = bruto.decode("latin-1").replace("\x00", "")
        linhas = texto.splitlines()
        if not linhas:
            raise ValueError("CSV vazio")

        cabecalho = linhas[0].split(DELIMITADOR)
        esperadas = len(cabecalho)
        inicio = 1
        if len(linhas) > 1:
            miolo = linhas[1].replace(DELIMITADOR, "").strip()
            if miolo and set(miolo) <= {"-"}:
                inicio = 2

        registros = []
        rejeitadas = []
        for numero, linha in enumerate(linhas[inicio:], start=inicio + 1):
            if not linha.strip():
                rejeitadas.append({"line_number": numero, "reason": "linha_vazia", "raw_line": linha})
                continue
            if linha.count(DELIMITADOR) != esperadas - 1:
                rejeitadas.append(
                    {"line_number": numero, "reason": "contagem_de_campos", "raw_line": linha[:500]}
                )
                continue
            registros.append(linha.split(DELIMITADOR))

        quadro = pd.DataFrame(registros, columns=cabecalho)
        quarentena = pd.DataFrame(rejeitadas, columns=["line_number", "reason", "raw_line"])
        info = {
            "bytes_nulos": bytes_nulos,
            "colunas": esperadas,
            "mascara_ignorada": inicio == 2,
        }
        return quadro, quarentena, info

    def tipar(self, nome_tabela, quadro):
        tipado = quadro.copy()
        for coluna in tipado.columns:
            texto = tipado[coluna].astype("string").str.strip()
            tipado[coluna] = texto.mask(texto == "", pd.NA)

        datas_invalidas = {}
        numeros_invalidos = {}
        for coluna in COLUNAS_DATA.get(nome_tabela, []):
            if coluna not in tipado.columns:
                continue
            original = tipado[coluna]
            convertida = pd.to_datetime(original, errors="coerce")
            datas_invalidas[coluna] = int((original.notna() & convertida.isna()).sum())
            tipado[coluna] = convertida

        for coluna in COLUNAS_NUMERO.get(nome_tabela, []):
            if coluna not in tipado.columns:
                continue
            texto = tipado[coluna].astype("string").str.strip()
            texto = texto.mask(texto == "", pd.NA)
            tem_virgula = texto.str.contains(",", na=False)
            normalizado = texto.where(
                ~tem_virgula,
                texto.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
            )
            numero = pd.to_numeric(normalizado, errors="coerce")
            numeros_invalidos[coluna] = int((texto.notna() & numero.isna()).sum())
            tipado[coluna] = numero

        return tipado, {"datas_invalidas": datas_invalidas, "numeros_invalidos": numeros_invalidos}

    def deduplicar(self, quadro, chave):
        contagem = {"chaves_nulas": 0, "duplicatas_exatas": 0, "duplicatas_divergentes": 0}
        if not chave or any(coluna not in quadro.columns for coluna in chave):
            return quadro, contagem

        sem_chave = quadro[chave].isna().any(axis=1)
        contagem["chaves_nulas"] = int(sem_chave.sum())
        com_chave = quadro.loc[~sem_chave].copy()

        repetida = com_chave.duplicated(keep="first")
        contagem["duplicatas_exatas"] = int(repetida.sum())
        com_chave = com_chave.loc[~repetida]

        mesma_chave = com_chave.duplicated(subset=chave, keep=False)
        contagem["duplicatas_divergentes"] = int(com_chave.loc[mesma_chave, chave].drop_duplicates().shape[0])
        com_chave = com_chave.drop_duplicates(subset=chave, keep="first")
        return com_chave, contagem
