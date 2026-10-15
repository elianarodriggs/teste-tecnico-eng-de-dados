# Decisões técnicas e qualidade

## Leitura dos CSV

| Tema | Decisão | Efeito |
|------|---------|--------|
| Encoding | Latin-1 na Silver | Compatível com o cp1252 do extrato; acentos de assunto e bairro permanecem |
| Delimitador | `;` | Como publicado pelo C3SL |
| Linha 2 | Ignorada quando é máscara de traços | Não vira dado |
| Campo com `;` não escapado | Linha **descartada** se a contagem de campos não fecha | Não há reparo manual. A quantidade fica em `rows_dropped_parse` no manifesto da Silver |
| Byte nulo (`0x00`) em texto | Removido na Silver | Vira vazio e, em seguida, nulo. A Bronze mantém o byte original |
| Bronze | Bytes originais, sem inferir tipo | Dá para reprocessar a Silver sem baixar de novo |

Premissa: uma linha com o número certo de `;`, mas com o valor deslocado para a coluna vizinha, não é detectada. Só o desbalanceamento é.

## Chaves e relacionamentos

- `SERVICO_SOLICITADO.SSO_IDF` identifica a solicitação.
- `SERVICO.SSO_IDF` aponta para a solicitação (1:N).
- `SERVICO_EXECUTADO.SER_IDF` aponta para o serviço (1:N).
- `SITUACAO_SOLICITACAO` é histórico por `SSO_IDF`. A situação vigente já está em `SIT_IDF_ATUAL` na solicitação, então o histórico não entra na Gold principal.
- `OSO_IDF` vazio significa solicitação sem ordem de serviço (`tem_oso = false`).
- `TIPO_SERVICO` (`TSE_COD`, `TSE_DESC`) não encontra chave em `SSO_COD_ASSUNTO156` nem em `SSO_ASSUNTO`. Fica na Silver, sem join forçado.
- `GTMBAIBAIRRO` repete o nome que a solicitação já traz em `SSO_NOME_BAIRRO`. A Gold usa o nome da solicitação.

## Silver

- Chave nula: linha fora (`SSO_IDF`, `SER_IDF`, `SEE_IDF`, `TSE_COD`, `COD_BAIRRO`, quando a chave existe).
- Duplicidade da chave: fica a primeira ocorrência.
- Data: `pandas.to_datetime`, inválida vira nulo.
- Decimal com vírgula: troca para ponto antes do numérico.
- String vazia ou só com espaço: nulo.
- `SITUACAO_SOLICITACAO` não tem chave única neste desenho. O histórico inteiro é mantido.

## Gold — regras

| Regra | Escolha |
|-------|---------|
| Grão do fato | 1 linha por `SSO_IDF`. Volume de solicitações não duplica quando há vários serviços |
| Grão do agregado | `regional` × `assunto` (`SSO_REGIONAL`, `SSO_ASSUNTO`) |
| Vários serviços | Conta serviços distintos; datas mínima e máxima de execução; soma quantidade e valor dos itens |
| Abertura | `SSO_DATA_SOLICITACAO` |
| Execução | Primeira `SER_DATA_EXECUCAO` da solicitação |
| Tempo | Horas entre abertura e primeira execução. Se não houver data de execução, usa `SSO_DATA_REALIZACAO` |
| Tempo negativo | Execução ou realização anterior à abertura sai da métrica (nulo) e liga `tempo_negativo`. Não usa o fallback quando a execução existe e está inconsistente |
| Sem execução | A solicitação continua no fato. Tempo nulo. Quantidade e valor zero. Entra em `pct_sem_execucao` |
| Regional ou assunto vazio | `NÃO INFORMADO` |
| Caixa do rótulo | Regional, assunto e bairro vão para maiúsculas na Gold, com espaço interno colapsado. O extrato grava a mesma regional como `UNIDADE REGIONAL BOA VISTA` e `Unidade Regional Boa Vista`. A Silver guarda o texto original |
| Valor do item | `SEE_VALOR_TOTAL`. Se vier vazio e quantidade e valor unitário existirem, usa o produto. Se só o unitário existir, o valor fica nulo — não se assume quantidade 1 |
| Órfão | Serviço sem `SSO_IDF` deste recorte, ou item sem `SER_IDF`, não entra no fato. A contagem vai para `qualidade_integracao` |

## O que a Gold responde agora

- Volume, tempo médio, tempo mediano, quantidade e valor por regional e assunto.
- Proporção sem `OSO_IDF` e sem execução registrada, no mesmo agregado.
- Existência de serviço sem solicitação, item sem serviço e item sem valor, no quadro de integração.

## O que ficou para depois

- Funil por `SIT_IDF_ATUAL` contra existência de serviço executado. A coluna já está no fato.
- Pendência por regional usando o histórico de `SITUACAO_SOLICITACAO`.
- Indicador oficial de valor. Antes disso é preciso tratar a massa de `SEE_VALOR_TOTAL` vazio e o desencontro entre serviço antigo e solicitação deste recorte.
- De-para de `TIPO_SERVICO` / código 156, que este extrato não permite.

## O que não foi escondido

- Linha quebrada é perda de volume, registrada no manifesto.
- Tempo mediano ignora duração negativa em vez de publicá-la como atendimento.
- Valor executado está subcontado onde o extrato não traz total nem o par quantidade × unitário.
- Quantidade executada soma unidades diferentes (m², unidade, trecho). Serve como grandeza dentro do mesmo assunto, com ressalva, e não como ranking único entre assuntos.

## Achados deste recorte (2016-09-21)

Segunda execução do pipeline reproduziu os mesmos totais.

| Medida | Valor |
|--------|-------|
| Solicitações na Gold | 50.017 |
| Serviços / itens na Silver | 337.018 / 715.973 |
| Linhas CSV descartadas | 2 em solicitação, 1 em serviço |
| Serviços sem solicitação neste recorte | 310.165 (92%) |
| Solicitações sem serviço | 28.056 (56%) |
| Solicitações sem execução registrada | 28.007 (56%) |
| Durações negativas, fora da métrica | 12.922 |
| Durações válidas | 9.088 |
| Regionais depois da normalização de caixa | 10 |
| `OSO_IDF` distinto | 6 valores, nenhum nulo |

`OSO_IDF` não se comporta como número de ordem: está preenchido em todas as solicitações e só assume os códigos 6, 2, 8, 7, 3 e 4. A proporção sem OSO é zero, e o campo não sustenta indicador de ordem de serviço.
