# Definições das fontes

`sources.yaml` é a única lista de tabelas do recorte. O job de Bronze lê esse arquivo para baixar cada CSV e gravar o arquivo original em `lake/bronze/{tabela}/`. A Silver usa a mesma lista para saber a chave natural. URL, nome do arquivo e chave não ficam no código.

Neste desenho, o YAML cumpre o papel das declarações da camada raw: diz de onde vem o dado e qual é a chave, sem regra de negócio.

## Campos

| Campo | Função |
|---|---|
| `snapshot_date` | Recorte dos arquivos. Vira a partição `snapshot_date=2016-09-21` nas três camadas. |
| `base_url` | Espelho público. A URL de cada tabela é `base_url` + `file`. |
| `tables` | Uma entrada por tabela. A chave do bloco (`servico_solicitado`) é o nome lógico no lake. |
| `file` | Nome do CSV no espelho, preservado no manifesto da Bronze. |
| `primary_key` | Colunas da chave natural. A Silver deduplica por elas. Lista vazia mantém todas as linhas, como em `situacao_solicitacao`, que é histórico. |

## Tabelas deste recorte

| Nome lógico | Chave | Papel |
|---|---|---|
| `servico_solicitado` | `SSO_IDF` | Pedido. Núcleo da Gold. |
| `servico` | `SER_IDF` | Serviço ligado ao pedido. |
| `servico_executado` | `SEE_IDF` | Item executado, com quantidade e valor. |
| `situacao_solicitacao` | nenhuma | Histórico de situação. Fica na Silver. |
| `gtmbaibaibairro` | `COD_BAIRRO` | Dimensão de bairro. |
| `tipo_servico` | `TSE_COD` | Dimensão de tipo. Sem chave compatível com o pedido neste recorte. |

## Incluir outra tabela do mesmo espelho

Acrescente um bloco em `tables` e rode o pipeline de novo. Não é preciso alterar o job de Bronze.

```yaml
nova_tabela:
  file: "2016-09-21_Sigmu_-_NOVA_TABELA_-_Base_de_Dados.csv"
  primary_key: [ID_DA_TABELA]
```

O objeto cai em `bronze/nova_tabela/snapshot_date=2016-09-21/data.csv`. Se a tabela entrar na Gold, o join continua em `src/sigmu_pipeline/jobs/gold.py`: o YAML não descreve relacionamento.
