# Solução — Pipeline SIGMU (Curitiba)

## Visão geral

Pipeline reproduzível em três camadas, no padrão medalhão, com storage compatível com S3 (SeaweedFS) e um DAG em Python. A organização segue o desenho habitual de uma plataforma de dados em GCP:

| Papel na plataforma | Neste projeto |
|---------------------|---------------|
| Camada raw: declaração da fonte e landing fiel | `definitions/sources.yaml` + `jobs/bronze.py` |
| Camada curated: modelos tipados, ainda no grão da origem | `jobs/silver.py` |
| Consumo analítico em cima da curated | `jobs/gold.py` (fato + agregado) |
| Orquestração por DAG | `orchestration/dag_sigmu_daily.py` |

O runtime local não é BigQuery. O contrato é o mesmo: objeto bruto imutável em relação à origem, tabela curada e tabela de consumo, com partição e linhagem. O storage faz o papel do bucket de objetos; o Parquet faz o papel da tabela analítica.

```text
[C3SL/UFPR — CSV públicos, recorte 2016-09-21]
                 |
                 v
        landing_bronze          bytes originais + _manifest.json
                 |
                 v
        curated_silver          Parquet tipado, deduplicado
                 |
                 v
        consumo_gold            fato por solicitação
                                 agregado regional × assunto
```

Relacionamento usado na Gold:

```text
SERVICO_SOLICITADO 1 ──< N SERVICO 1 ──< N SERVICO_EXECUTADO
        SSO_IDF                 SER_IDF
```

`SITUACAO_SOLICITACAO`, `TIPO_SERVICO` e `GTMBAIBAIRRO` entram na Bronze e na Silver. A pergunta principal não depende delas; o motivo está em `docs/decisoes.md`.

## Como subir o ambiente

Na raiz deste repositório:

```bash
cp .env.example .env
docker compose up -d
```

O endpoint S3 fica em `http://localhost:8333`. Ajustes em relação ao ambiente da banca:

- `.env.example` declara `S3_ENDPOINT`.
- `docker-compose.yml` ganhou o serviço `pipeline` (profile `pipeline`), que enxerga o storage como `http://seaweedfs:8333`.
- Nesta rede o TLS é interceptado. O build do container usa `--trusted-host` no pip, e o serviço monta o bundle de CAs da máquina (`REQUESTS_CA_BUNDLE`) para o download do C3SL. Em uma rede sem interceptação, o volume pode sair e o pip volta a verificar o certificado normalmente.

Nesta máquina o usuário não está no grupo `docker`. Os comandos do Makefile funcionam com `sudo docker compose` no lugar de `docker compose`, ou depois de incluir o usuário no grupo.

Interfaces do storage:

- S3: `http://localhost:8333`
- Filer: `http://localhost:8888`
- Master: `http://localhost:9333`

## Como executar

Pipeline completo, na ordem bronze, silver, gold:

```bash
make pipeline
```

O mesmo fluxo pelo DAG (`landing_bronze >> curated_silver >> consumo_gold`):

```bash
make pipeline-dag
```

Testes (parser, chaves de partição e regras da Gold):

```bash
make test
```

Ranking da Gold e quadro de integração:

```bash
make inspect
```

Uma etapa isolada, se precisar reprocessar só a curadoria ou só o consumo:

```bash
docker compose --profile pipeline run --rm pipeline silver
docker compose --profile pipeline run --rm pipeline gold
```

## Onde estão os dados

Bucket `lake`. Todos os objetos do recorte ficam na partição `snapshot_date=2016-09-21`.

| Camada | Caminho | Conteúdo |
|--------|---------|----------|
| Bronze | `bronze/{tabela}/snapshot_date=2016-09-21/data.csv` | CSV original, byte a byte |
| Bronze | `.../_manifest.json` e `.../_SUCCESS` | URL, data da extração, sha256, marcador de carga |
| Silver | `silver/{tabela}/snapshot_date=2016-09-21/data.parquet` | Tabela tipada |
| Gold | `gold/fato_solicitacao_execucao/.../data.parquet` | 1 linha por `SSO_IDF` |
| Gold | `gold/agregado_regional_assunto/.../data.parquet` | 1 linha por regional e assunto |
| Gold | `gold/qualidade_integracao/.../data.parquet` | contagens de órfãos, tempo negativo e valor ausente |

Tabelas: `servico_solicitado`, `situacao_solicitacao`, `servico`, `servico_executado`, `gtmbaibaibairro`, `tipo_servico`.

## Pergunta de negócio

> Quais tipos de serviço e regiões concentram maior volume de solicitações, maior tempo de atendimento e maior valor executado?

A resposta está em `agregado_regional_assunto` e no rollup do fato por regional ou por assunto. Números do recorte, estáveis na segunda execução:

- **Volume:** Boa Vista (10.655 solicitações) e o assunto pavimentação alternativa / antipó (11.374).
- **Tempo:** mediana mais alta na Boa Vista, da ordem de 40 a 60 dias, calculada só sobre as 9.088 durações válidas.
- **Valor:** manutenção corretiva de pavimentação (R$ 7,8 milhões), concentrada em Bairro Novo, Portão e Santa Felicidade. Quase não há tempo válido nesse grupo.

O detalhe e o roteiro de fala estão nos comentários de `docs/apresentacao.md`. Os slides para a defesa estão em `docs/apresentacao.pdf` (17 páginas, cerca de 20 minutos). Consulta pronta: `scripts/consulta_gold.sql`.

## Reexecução

A partição é fixa. Rodar de novo sobrescreve `data.csv`, `data.parquet`, `_manifest.json` e `_SUCCESS` da mesma chave. Não há append, então o resultado não duplica. O manifesto é reescrito com um novo `extracted_at_utc`; o `sha256` da Bronze permanece o mesmo se o arquivo de origem não mudou.

```bash
make pipeline
make pipeline
make inspect
```

Falha numa etapa do DAG interrompe as seguintes. O log da tarefa (`task start` / `task success`) mostra até onde a carga chegou.

## Testes

`make test` cobre:

- descarte da linha de máscara e de linhas com delimitador quebrado;
- estabilidade do caminho `snapshot_date=2016-09-21`;
- soma de vários serviços na mesma solicitação, permanência de solicitação sem execução, exclusão de órfão e tempo negativo fora da métrica.

## Limitações

- O DAG é um script. Não há scheduler; em produção ele seria agendado pelo orquestrador.
- Órfão e tempo negativo não falham a carga. Ficam contados em `qualidade_integracao`.
- `SSO_ASSUNTO` representa o tipo na pergunta de negócio. `TIPO_SERVICO` fica só na Silver.
- `SEE_VALOR_TOTAL` vazio não é inventado a partir do valor unitário quando a quantidade também está vazia.
- Linha de CSV com quantidade de campos errada é descartada, não reparada. A contagem vai para o manifesto da Silver.
- Um único snapshot. Não há histórico incremental.
- `SITUACAO_SOLICITACAO` não entra na métrica principal. `SIT_IDF_ATUAL` fica no fato para uma análise posterior.

## Próximos passos

- Assertions de chave e de relacionamento na curated, no mesmo espírito de testes de modelo (chave única, relacionamento resolvido), bloqueando indicador oficial quando o órfão passar de um limite.
- Partições por data de extração, em vez de sobrescrever o único snapshot.
- Publicar o Parquet como tabela externa e manter o agregado como tabela nativa de consumo.
- Agendar o DAG e alertar drift de schema quando o cabeçalho do C3SL mudar.
- Enriquecer assunto com uma dimensão de tipo que tenha chave de verdade, e bairro pela `GTMBAIBAIRRO` quando `SSO_NOME_BAIRRO` vier vazio.
- Painel em cima de `agregado_regional_assunto`, com volume, tempo mediano e valor lado a lado.

Decisões de qualidade: `docs/decisoes.md`. Desenho das camadas: `docs/arquitetura.md`. Roteiro da defesa: `docs/apresentacao.md`.
