# Como rodar

O `README.md` da raiz é o da banca. Este aqui é o passo a passo da solução.

Pasta do projeto > execução

```bash
cd ~/me/facul-trab/trabalho/teste-tecnico-eng-de-dados
```

## Ordem

Um comando só faz as três etapas, nesta ordem:

1. **bronze** — baixa o CSV do C3SL e grava no SeaweedFS, no bucket `lake`
2. **silver** — lê a bronze, tipa e separa linha quebrada
3. **gold** — monta uma linha por solicitação

A entrada é `src/main.py`.

| Peça | Arquivo |
|---|---|
| entrada | `src/main.py` |
| bronze, silver e gold | `src/pipeline.py` |
| leitura do CSV | `src/leitor.py` |
| SeaweedFS | `src/lago.py` |
| lista das fontes | `src/configuracao.py` |
| SQL da gold | `sql/gold.sql` |
| ranking na tela | `scripts/inspect_gold.py` |

`sql/consultas.sql` não entra no pipeline. São as três consultas da pergunta, para rodar em cima do agregado.

## Cookbook

```bash
cp .env.example .env
sudo docker compose up -d
sudo docker compose --profile pipeline run --rm pipeline all
```

O `all` já chama bronze, silver e gold. Para rodar uma etapa sozinha:

```bash
sudo docker compose --profile pipeline run --rm pipeline bronze
sudo docker compose --profile pipeline run --rm pipeline silver
sudo docker compose --profile pipeline run --rm pipeline gold
```

Silver e gold usam a pasta do dia. Se a bronze desse dia não existir, a etapa falha.

Ver o ranking:

```bash
sudo docker compose --profile pipeline run --rm --no-deps --entrypoint python pipeline /app/scripts/inspect_gold.py
```

Testes:

```bash
sudo docker compose --profile pipeline run --rm --entrypoint pytest pipeline -q
```

O mesmo pelo Makefile, também com `sudo`:

```bash
sudo make up
sudo make pipeline
sudo make inspect
sudo make test
sudo make down
```

## Onde ficam os dados

No volume Docker `seaweedfs_data`, bucket `lake`. 

- Filer: http://localhost:8888
- S3: http://localhost:8333
- Master: http://localhost:9333

A pasta é `extraction_date`, o dia em que o pipeline rodou. `2016-09-21` é o período do arquivo.

| Camada | Caminho |
|---|---|
| Bronze | `bronze/{tabela}/extraction_date=AAAA-MM-DD/{arquivo original}.csv` |
| Silver | `silver/{tabela}/extraction_date=AAAA-MM-DD/data.parquet` |
| Qualidade | `silver/_quality/extraction_date=AAAA-MM-DD/` |
| Gold | `gold/fato_solicitacao/extraction_date=AAAA-MM-DD/data.parquet` |
| Gold | `gold/agregado_regional_assunto/extraction_date=AAAA-MM-DD/data.parquet` |

Rodar de novo no mesmo dia substitui a mesma pasta.

As regras estão em `docs/decisoes.md`. O resultado e as limitações estão em `docs/solucao.md`. A apresentação está em `docs/apresentacao.pdf`.
