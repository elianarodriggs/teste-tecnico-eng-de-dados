# Solução — Pipeline SIGMU

Pipeline em três camadas no bucket `lake`. A Bronze guarda o CSV original. A Silver tipa e limpa. A Gold responde a pergunta de negócio.

```text
C3SL (CSV, 2016-09-21)
        |
        v
     bronze          CSV original + manifesto
        |
        v
     silver          Parquet tipado
        |
        v
      gold           1 linha por solicitação
                     agregado por regional e assunto
```

```text
SERVICO_SOLICITADO 1 ──< N SERVICO 1 ──< N SERVICO_EXECUTADO
```

O código fica em `src/sigmu_pipeline/jobs/`. A ordem de execução é `bronze`, depois `silver`, depois `gold`.

## Subir o ambiente

Na raiz deste repositório:

```bash
cp .env.example .env
docker compose up -d
```

S3 em `http://localhost:8333`. Filer em `http://localhost:8888`. Master em `http://localhost:9333`.

Ajustes locais: o `docker-compose.yml` tem o serviço `pipeline`, que fala com o storage em `http://seaweedfs:8333`. Nesta rede o TLS é interceptado, então o build usa `--trusted-host` no pip e o container monta o bundle de CAs da máquina. Nesta máquina os comandos Docker precisam de `sudo`.

## Executar

```bash
sudo docker compose --profile pipeline run --rm pipeline all
```

Etapas separadas: `bronze`, `silver` ou `gold` no lugar de `all`.

Testes:

```bash
sudo docker compose --profile pipeline run --rm --entrypoint pytest pipeline -q
```

Ranking da Gold:

```bash
sudo docker compose --profile pipeline run --rm --no-deps --entrypoint python pipeline /app/scripts/inspect_gold.py
```

A consulta equivalente está em `scripts/consulta_gold.sql`. A apresentação está em `docs/apresentacao.pdf`.

## Onde estão os dados

Partição `snapshot_date=2016-09-21`.

| Camada | Caminho | Conteúdo |
|---|---|---|
| Bronze | `bronze/{tabela}/snapshot_date=2016-09-21/data.csv` | CSV original |
| Silver | `silver/{tabela}/snapshot_date=2016-09-21/data.parquet` | Tabela tipada |
| Gold | `gold/fato_solicitacao_execucao/.../data.parquet` | 1 linha por `SSO_IDF` |
| Gold | `gold/agregado_regional_assunto/.../data.parquet` | regional × assunto |
| Gold | `gold/qualidade_integracao/.../data.parquet` | órfãos e tempos inválidos |

Cada prefixo tem `_manifest.json` (origem, data da extração, contagens) e `_SUCCESS`.

Tabelas: `servico_solicitado`, `servico`, `servico_executado`, `situacao_solicitacao`, `gtmbaibaibairro`, `tipo_servico`.

## Decisões

| Tema | Escolha |
|---|---|
| Leitura | Latin-1, delimitador `;`, linha de máscara ignorada |
| Linha com `;` a mais ou a menos | Descartada e contada no manifesto da Silver. Foram 3 linhas no recorte |
| Bronze | Bytes originais, sem tipo |
| Chave | Dedup por `SSO_IDF`, `SER_IDF`, `SEE_IDF`. Situação não tem chave: é histórico |
| Grão da Gold | 1 solicitação. Vários serviços somam quantidade e valor |
| Tipo de serviço | `SSO_ASSUNTO`. `TIPO_SERVICO` não tem chave compatível e fica só na Silver |
| Região | `SSO_REGIONAL`, em maiúsculas, para unir a mesma regional escrita de dois jeitos |
| Tempo | Horas até a primeira execução. Sem data de execução, usa a data de realização. Data anterior à abertura fica de fora |
| Sem execução | A solicitação permanece no fato, com tempo nulo |
| Valor | `SEE_VALOR_TOTAL`. Se vier vazio e houver quantidade e valor unitário, usa o produto |
| Órfão | Serviço sem solicitação deste recorte não entra no fato. A contagem fica em `qualidade_integracao` |
| Reexecução | A mesma partição é sobrescrita. A segunda rodada repetiu 50.017 solicitações |

## Resultado

- Volume: Boa Vista, 10.655 solicitações. Assunto mais frequente: pavimentação alternativa / antipó, 11.374.
- Tempo: 9.088 durações válidas. As medianas mais longas, com amostra, estão na Boa Vista (cerca de 40 a 60 dias).
- Valor: manutenção corretiva de pavimentação, R$ 7,8 milhões, concentrada em Bairro Novo, Portão e Santa Felicidade. Nesse grupo quase não há tempo válido.

`OSO_IDF` está preenchido em todas as linhas e só tem seis códigos. Não serve como número de ordem.

## Limitações

- 92% dos serviços não encontram solicitação neste recorte. A carga segue e o número fica registrado.
- Quantidade soma unidades diferentes. Não entra no ranking entre assuntos.
- Um único snapshot. Sem scheduler.
- `SITUACAO_SOLICITACAO` não entra na métrica. `SIT_IDF_ATUAL` fica no fato para uma análise posterior.

## Próximos passos

- Falhar a publicação da Gold se o percentual de órfãos passar de um limite.
- Guardar mais de um snapshot, em vez de sobrescrever o recorte.
- Painel em cima de `agregado_regional_assunto`.
- Só cruzar `TIPO_SERVICO` quando existir chave de verdade.
