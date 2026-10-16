# Decisões

Cada item abaixo está implementado.

## Extração e período

A data no nome do arquivo, `2016-09-21`, é o período do dataset. A partição `extraction_date` é o dia em que o pipeline roda, no fuso `America/Sao_Paulo`. As duas datas não são a mesma coisa.

## Bronze

Os bytes do CSV são gravados sem mudar encoding nem delimitador. O nome original do arquivo é o nome do objeto. O manifesto guarda URL, período, data de extração, tamanho e sha256.

As quatro tabelas do núcleo são obrigatórias: se o download falhar, o pipeline para. Bairro e tipo de serviço são opcionais: a falha aparece no log e a carga segue.

A reexecução no mesmo dia usa a mesma chave e substitui o objeto.

## Leitura

| Tema | Decisão |
|---|---|
| Encoding | Latin-1 na Silver. A Bronze permanece em bytes |
| Delimitador | `;` |
| Linha de máscara | Ignorada |
| Linha com contagem de campos errada | Vai para `silver/_quality/.../quarentena.parquet`, com motivo `contagem_de_campos`. Não é corrigida |
| Byte nulo no texto | Removido na Silver. A quantidade de bytes removidos entra na métrica |
| Vazio | Vira nulo. Nulo não vira zero |
| ID | Texto, para não perder zero à esquerda |
| Número | Ponto é decimal, como em `2.03`. Vírgula, se existir, é tratada como decimal |
| Data inválida | Nulo, e a quantidade entra na métrica |

No recorte, a quarentena teve 3 linhas: 2 em solicitação e 1 em serviço. Não houve chave nula nem duplicidade.

## Relacionamento

`SERVICO.SSO_IDF` aponta para a solicitação. `SERVICO_EXECUTADO.SER_IDF` aponta para o serviço. A situação é histórico por `SSO_IDF`, não uma tabela de domínio, e por isso não entra no join da Gold.

`TIPO_SERVICO` não se liga a `SSO_ASSUNTO` nem a `SSO_COD_ASSUNTO156`. Não forcei esse join.

## Silver

A chave natural deduplica. Duplicata exata sai, com contagem. A mesma chave com conteúdo diferente fica com a primeira ocorrência e a chave é contada como divergente. Isso não apareceu neste recorte.

Chave nula sai da tabela e vai para a quarentena. Também não apareceu.

## Gold

O grão é uma solicitação (`SSO_IDF`). O assunto está no pedido, então uma linha por solicitação já é uma linha por tipo disponível. Não dá para abrir uma linha por tipo da dimensão `TIPO_SERVICO`.

Os itens são somados por serviço, e os serviços por solicitação, antes de juntar ao pedido. Vários itens não multiplicam a solicitação. A validação interrompe a carga se a Gold tiver mais linhas do que solicitações na Silver.

| Regra | Escolha |
|---|---|
| Volume | Solicitações distintas |
| Tipo | `SSO_ASSUNTO`, em maiúsculas |
| Região | `SSO_REGIONAL`, em maiúsculas. Vazio vira `NÃO INFORMADO` |
| Execução | Existe serviço ligado. Sem serviço, `possui_execucao = 0` e a solicitação continua no fato |
| Tempo | Horas até a primeira `SER_DATA_EXECUCAO`. Sem essa data, usa `SSO_DATA_REALIZACAO` |
| Tempo negativo | Fica de fora da média e da mediana e é contado |
| Quantidade e valor | Soma dos itens. Ausente continua nulo. Se o total do item vier vazio e houver quantidade e valor unitário, usa o produto |
| Órfão | Serviço sem solicitação deste recorte não entra no fato. A contagem fica na validação |

## O que a execução mostrou

- 50.017 solicitações na Silver e na Gold.
- 28.056 sem serviço ligado.
- 12.922 tempos negativos e 9.088 tempos válidos.
- 310.165 serviços sem solicitação neste recorte.
- 2 itens sem serviço.
- Valor executado somado: R$ 13.510.408,43.
