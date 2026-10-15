# Arquitetura

## Princípios

1. **Raw imutável em relação à origem.** A Bronze grava o arquivo do C3SL sem interpretar coluna, tipo ou regra de negócio.
2. **Curated no grão da fonte.** A Silver resolve encoding, máscara, tipo, nulo e duplicidade. Ainda não responde à pergunta de negócio.
3. **Consumo com grão explícito.** A Gold só existe para a pergunta: uma linha por solicitação e um agregado por regional e assunto.
4. **Declaração separada do job.** URL, recorte e chave ficam em `definitions/sources.yaml`. O job de landing não tem nome de arquivo hardcoded.
5. **Linhagem por objeto.** Cada prefixo tem `_manifest.json` (`source_url` ou objeto de origem, `snapshot_date`, `extracted_at_utc`) e `_SUCCESS`.
6. **Job sem estado.** O container não guarda dados. Reprocessar é rodar de novo a mesma partição.

## Como isso se mapeia ao medalhão em GCP

| Camada | O que acontece no GCP | O que este repositório faz |
|--------|----------------------|----------------------------|
| Bronze / raw | Projeto de definições da camada raw: a fonte é declarada e o arquivo aterrissa sem regra de negócio | `definitions/sources.yaml` + `src/sigmu_pipeline/jobs/bronze.py` |
| Silver / curated | Modelos da camada curated: tipo, deduplicação, chave natural, ainda 1:1 com a origem | `src/sigmu_pipeline/jobs/silver.py` |
| Gold / consumo | Modelos de consumo publicados a partir da curated, com grão analítico | `src/sigmu_pipeline/jobs/gold.py` |
| Orquestração | DAG em Python: landing, depois curated, depois consumo. Falha interrompe a sequência | `orchestration/dag_sigmu_daily.py` |
| Storage | Bucket de objetos para o arquivo bruto; tabela analítica para o que já foi curado | SeaweedFS, bucket `lake`, Parquet na Silver e na Gold |

A Gold deste teste é a camada de consumo. No GCP ela entra no mesmo fluxo da curated, como modelo final, e o DAG é quem garante a ordem. Não há transformação de negócio na raw.

## Componentes

```text
docker-compose.yml
├── seaweedfs                 S3 em :8333, filer :8888, master :9333
└── pipeline (profile)        Python 3.11, pandas, pyarrow, boto3

src/sigmu_pipeline/
├── config.py                 ambiente + sources.yaml + prefixo da partição
├── csv_source.py             download e parser do CSV
├── io.py                     cliente S3, Parquet, manifesto
├── quality.py                nulos, tipos, dedup, duração
└── jobs/
    ├── bronze.py
    ├── silver.py
    └── gold.py

orchestration/dag_sigmu_daily.py
    landing_bronze >> curated_silver >> consumo_gold
```

## Contrato do lake

- Bucket: `lake`
- Prefixos: `bronze/`, `silver/`, `gold/`
- Partição do teste: `snapshot_date=2016-09-21`
- Reexecução: `put` na mesma chave, sem segunda cópia

## Fluxo da Gold

1. Lê a Silver de solicitação, serviço e item executado.
2. Agrega serviço por `SSO_IDF` (quantidade de serviços, primeira e última execução).
3. Soma quantidade e valor do item pelo `SER_IDF`, já resolvido até a solicitação.
4. Publica o fato (`SSO_IDF`) com solicitação sem execução preservada.
5. Agrega o fato por `regional` e `assunto`.
6. Publica `qualidade_integracao` com órfãos e tempos inconsistentes, sem misturar isso no indicador.

## Evolução, sem trocar o contrato

| Agora | Produção no mesmo desenho |
|-------|---------------------------|
| SeaweedFS | Bucket gerenciado |
| `docker compose run pipeline` | DAG agendado chamando o mesmo container |
| Parquet no lake | Tabela externa para a Silver; tabela nativa para a Gold |
| YAML de fontes | Declarações versionadas da camada raw |
| Manifesto JSON | Metadados de execução e teste de qualidade bloqueante |
