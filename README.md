# Teste Técnico — Engenharia de Dados

## Bem-vindo(a)

Este repositório contém o ambiente inicial do teste técnico de Engenharia de Dados. O caso utiliza dados públicos do **Sistema Integrado de Gestão da Manutenção Urbana (SIGMU)**, de Curitiba.

O objetivo é construir um pipeline pequeno, reproduzível e documentado, capaz de organizar dados brutos em camadas e gerar uma visão analítica para responder a uma pergunta de negócio.

O tempo esperado de implementação é de **4 a 6 horas**. Não é necessário implementar tudo. Priorize uma solução funcional, clara e bem justificada.

## Versionamento da entrega

O desenvolvimento deve ser versionado com Git desde o início. O histórico fará parte da avaliação técnica e deve permitir compreender a evolução da solução.

Serão observadas a organização das mudanças, a clareza das mensagens e a rastreabilidade das decisões. Evite entregar todo o trabalho em um único commit ou apagar o histórico antes da entrega. Não inclua credenciais reais, arquivos sensíveis ou dados desnecessários no repositório.

## Contexto técnico fornecido

O ambiente já inclui um storage local compatível com S3 usando SeaweedFS.

Durante o teste, será permitido e necessário acesso à internet para baixar os arquivos públicos do SIGMU no C3SL/UFPR.

```text
Endpoint S3: http://localhost:8333
Access key: admin
Secret key: change-me
Bucket: lake
```

O bucket `lake` será usado com os prefixos `bronze/`, `silver/` e `gold/`.

Interfaces de inspeção:

- Filer UI: <http://localhost:8888>
- Master UI: <http://localhost:9333>

## Etapa 1 — Preparar o ambiente

1. Crie o arquivo de configuração local:

   ```bash
   cp .env.example .env
   ```

2. Suba o storage:

   ```bash
   docker compose up -d
   ```

3. Confirme que o serviço está disponível e documente qualquer ajuste necessário.

## Etapa 2 — Conhecer as fontes

### Origem dos arquivos brutos

Os arquivos brutos deverão ser obtidos diretamente do espelho público do C3SL/UFPR:

<https://dadosabertos.c3sl.ufpr.br/curitiba/SIGMU/>

Para este teste, utilize o recorte de **21/09/2016** e as seguintes fontes:

O núcleo obrigatório é composto por `SERVICO_SOLICITADO`, `SITUACAO_SOLICITACAO`, `SERVICO` e `SERVICO_EXECUTADO`. As dimensões `GTMBAIBAIBAIRRO` e `TIPO_SERVICO` são opcionais e podem ser usadas para enriquecer a análise.

| Fonte | URL |
|---|---|
| `SERVICO_SOLICITADO` | <https://dadosabertos.c3sl.ufpr.br/curitiba/SIGMU/2016-09-21_Sigmu_-_SERVICO_SOLICITADO_-_Base_de_Dados.csv> |
| `SITUACAO_SOLICITACAO` | <https://dadosabertos.c3sl.ufpr.br/curitiba/SIGMU/2016-09-21_Sigmu_-_SITUACAO_SOLICITACAO_-_Base_de_Dados.csv> |
| `SERVICO` | <https://dadosabertos.c3sl.ufpr.br/curitiba/SIGMU/2016-09-21_Sigmu_-_SERVICO_-_Base_de_Dados.csv> |
| `SERVICO_EXECUTADO` | <https://dadosabertos.c3sl.ufpr.br/curitiba/SIGMU/2016-09-21_Sigmu_-_SERVICO_EXECUTADO_-_Base_de_Dados.csv> |
| `GTMBAIBAIRRO` | <https://dadosabertos.c3sl.ufpr.br/curitiba/SIGMU/2016-09-21_Sigmu_-_GTMBAIBAIRRO_-_Base_de_Dados.csv> |
| `TIPO_SERVICO` | <https://dadosabertos.c3sl.ufpr.br/curitiba/SIGMU/2016-09-21_Sigmu_-_TIPO_SERVICO_-_Base_de_Dados.csv> |

Os arquivos usam delimitador `;`, encoding compatível com `cp1252`/Latin-1 e uma segunda linha com máscaras de tipo. Há valores vazios e algumas linhas com delimitadores não escapados em campos textuais. A pessoa candidata deve escolher uma estratégia de leitura, investigar o impacto das linhas problemáticas e registrar o que foi corrigido, preservado ou descartado.

Identifique chaves, relacionamentos, datas, situações, localização, quantidade, valor e problemas de delimitador, encoding, nulos ou tipos. Registre premissas e dúvidas em `docs/decisoes.md` ou no README.

## Etapa 3 — Implementar a ingestão Bronze

Implemente um processo reproduzível que:

1. obtenha os arquivos do recorte SIGMU indicado no material de apoio;
2. carregue os dados brutos no bucket `lake`;
3. preserve nomes e conteúdo de origem tanto quanto possível;
4. organize os objetos em prefixos por tabela, como `lake/bronze/servico_solicitado/`;
5. registre origem, data da extração e período dos arquivos.

Você pode usar Python, SQL, ferramentas S3 ou outra abordagem, desde que a execução seja documentada e rode dentro de containers Docker. O SeaweedFS é o storage fornecido, mas você pode substituí-lo por outra ferramenta compatível com S3, desde que ela seja conteinerizada, reproduzível e mantenha o contrato do teste: bucket `lake` com os prefixos `bronze/`, `silver/` e `gold/`.

A avaliação não será baseada na capacidade de administrar especificamente o SeaweedFS. O foco está nas decisões de engenharia de dados, na organização das camadas, na qualidade dos dados e na capacidade de produzir uma Gold confiável.

## Etapa 4 — Construir a Silver

Crie tabelas ou arquivos tratados em `lake/silver/`.

No mínimo, trate delimitador e encoding, datas e horários, valores vazios, tipos numéricos, duplicidades, valores inconsistentes e o relacionamento entre solicitações, serviços e itens executados.

Documente o que foi corrigido, descartado ou mantido com ressalva. Não esconda problemas de qualidade sem registrar a decisão.

## Etapa 5 — Construir a Gold

Produza uma relação analítica em `lake/gold/` que una informações de solicitação e execução.

A Gold deve permitir responder:

> Quais tipos de serviço e regiões concentram maior volume de solicitações, maior tempo de atendimento e maior valor executado?

Defina e documente a granularidade da Gold, a regra para múltiplos serviços, as datas de abertura e execução, o cálculo do tempo, a agregação de quantidade/valor e o tratamento de solicitações sem execução.

A pergunta acima é o objetivo principal. Se houver tempo, complemente a Gold ou produza consultas adicionais para investigar também:

- quais assuntos ou tipos de serviço possuem maior volume de solicitações;
- quais regionais apresentam maior proporção de solicitações sem `OSO_IDF`;
- qual é o tempo médio e mediano entre solicitação e realização por assunto ou regional;
- quais tipos de serviço concentram maior quantidade e valor total executado;
- como a situação das solicitações se relaciona com a existência de serviços executados;
- quais regionais apresentam maior volume de solicitações pendentes ou sem realização registrada;
- se existem execuções sem solicitação correspondente ou sem quantidade e valor válidos;
- quais problemas de qualidade ou integração entre as tabelas deveriam ser investigados antes da publicação de um indicador oficial.

Não é necessário responder todas as perguntas. A pessoa candidata deve priorizar, justificar o recorte escolhido e indicar quais análises ficaram para uma etapa posterior.

## Etapa 6 — Garantir reexecução

Execute o pipeline mais de uma vez e verifique se resultados não são duplicados, objetos não ficam corrompidos, a execução é idempotente ou sua estratégia está documentada e as falhas são visíveis.

## Etapa 7 — Documentar a solução

O projeto deve conter, no mínimo:

```text
README.md
docker-compose.yml
docs/
  solucao.md
  arquitetura.md       # opcional, se fizer sentido separar
  decisoes.md           # opcional, se fizer sentido separar
src/ ou pipelines/
tests/                 # se aplicável
```

O `README.md` fornecido pela banca deve ser preservado e não deve ser substituído. A documentação da solução deve ser criada em `docs/solucao.md`, podendo ser complementada por outros arquivos em `docs/`.

O `docs/solucao.md` deve explicar como subir o ambiente, executar o pipeline, consultar os dados, localizar Bronze/Silver/Gold, entender as decisões e conhecer as limitações. Quando uma relação, fluxo ou arquitetura puder ser compreendida mais rapidamente de forma visual, considere usar um esquema, tabela ou diagrama junto à explicação.

## Etapa 8 — Preparar a apresentação

Prepare uma apresentação de aproximadamente **20 minutos** para a defesa técnica, cobrindo entendimento do problema, fontes, arquitetura, camadas, qualidade, resultados, reprocessamento, trade-offs e próximos passos. Priorize uma comunicação clara e objetiva; representações visuais podem ajudar a sintetizar fluxos, relações entre entidades e decisões arquiteturais.

## Entrega obrigatória

Entregue código-fonte, configuração Docker, documentação em `docs/solucao.md`, consultas, testes ou validações, apresentação em PDF e lista de limitações e próximos passos.

## Itens opcionais

Caso conclua o núcleo antes do limite de tempo, você pode implementar carga incremental, particionamento, testes adicionais, observabilidade, schema drift, orquestração ou uso justificado de dbt, dlt ou DuckDB.

Complexidade adicional não será valorizada por si só. Uma solução menor, executável e bem explicada é preferível a uma arquitetura sofisticada e incompleta.
