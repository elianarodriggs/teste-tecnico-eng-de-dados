---
marp: true
theme: default
paginate: true
size: 16:9
title: Pipeline SIGMU — arquitetura medalhão
---

<style>
section {
  font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  background: #f4f7fb;
  color: #1c2833;
  padding: 46px 58px 40px;
  font-size: 26px;
  line-height: 1.35;
}
h1 { color: #0e3a5d; font-size: 40px; margin: 0 0 12px; }
h2 { color: #0e3a5d; font-size: 32px; margin: 0 0 14px; }
strong { color: #0e3a5d; }
table { font-size: 18px; width: 100%; border-collapse: collapse; }
th { background: #0e3a5d; color: white; font-weight: 600; }
td, th { padding: 6px 10px; }
section.lead { background: #0e3a5d; color: #f4f7fb; }
section.lead h1, section.lead h2, section.lead strong { color: white; }
section.lead p { color: #d5e4f0; }
.sub { color: #5d6d7e; font-size: 20px; }
.grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
.grid2 { display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 22px; }
.card { background: white; border-top: 6px solid #1a5276; padding: 14px 16px 10px; }
.card h3 { margin: 0 0 6px; color: #0e3a5d; font-size: 22px; }
.num { font-size: 34px; font-weight: 700; color: #0e3a5d; line-height: 1.1; }
.flow { display: flex; gap: 10px; align-items: stretch; }
.step { background: white; flex: 1; padding: 12px 12px 8px; border-top: 6px solid #1a5276; }
.step b { display: block; color: #0e3a5d; font-size: 18px; margin-bottom: 4px; }
.step span { font-size: 16px; color: #34495e; }
footer { color: #7f8c9b; font-size: 14px; }
</style>

<!-- _class: lead -->

# Pipeline SIGMU
## Arquitetura medalhão para a manutenção urbana de Curitiba

Recorte de 21/09/2016 · defesa técnica · cerca de 20 minutos

<!--
Abertura, 30 segundos.

Obrigado. Vou mostrar um pipeline pequeno do SIGMU, o sistema de manutenção urbana de Curitiba, organizado em medalhão: Bronze, Silver e Gold.

O desenho segue o mesmo contrato que a gente usa em GCP. A camada raw aterrissa o arquivo sem regra de negócio. A camada curated tipa e conforma. A Gold é o consumo, e um DAG em Python garante a ordem. O storage daqui é local, compatível com S3. O contrato das camadas é o que importa, não o produto.

O recorte é o espelho público do C3SL de 21 de setembro de 2016. No final eu respondo a pergunta de negócio com três concentrações diferentes: volume, tempo e valor não caem no mesmo lugar.
-->

---

## Roteiro

| Bloco | Tempo |
|---|---|
| Problema e o que a pergunta exige do modelo | 4 min |
| Fontes e qualidade na origem | 4 min |
| Arquitetura medalhão, Bronze, Silver e Gold | 7 min |
| Resultados do recorte | 3 min |
| Reprocessamento, limites e evolução | 2 min |

<!--
30 segundos.

São cinco blocos. O miolo é a arquitetura, sete minutos, porque é ali que está a decisão de engenharia. Os resultados cabem em três minutos: a leitura é mais importante do que a tabela. Deixo os limites para o final, inclusive o que eu não publicaria como indicador oficial.
-->

---

## A pergunta

Dados públicos de solicitação de manutenção urbana.

**Quais tipos de serviço e quais regiões concentram maior volume, maior tempo de atendimento e maior valor executado?**

<div class="grid">
<div class="card"><h3>Volume</h3>conta solicitação, uma vez</div>
<div class="card"><h3>Tempo</h3>abertura até a primeira execução</div>
<div class="card"><h3>Valor</h3>soma dos itens executados</div>
</div>

<!--
2 minutos.

O SIGMU registra o pedido do cidadão, o serviço que a regional executa e os itens dessa execução, com quantidade e valor.

A pergunta parece uma só. São três métricas. Volume conta pedido. Tempo mede espera. Valor mede o que foi lançado na execução. Se eu misturar isso num ranking único, eu respondo outra coisa.

Por isso a Gold tem um fato no grão da solicitação e um agregado por regional e assunto. Dá para ordenar por qualquer uma das três colunas sem duplicar o pedido quando ele tem vários serviços.
-->

---

## O que a pergunta exige

<div class="grid2">
<div>

- **Grão do fato:** 1 linha por solicitação (`SSO_IDF`)
- **Tipo:** assunto do pedido (`SSO_ASSUNTO`)
- **Região:** regional (`SSO_REGIONAL`)
- **Vários serviços:** somar valor e quantidade; guardar a primeira e a última execução
- **Sem execução:** a solicitação continua no fato

</div>
<div class="card">
<h3>Por que assunto, e não a dimensão de tipo</h3>
`TIPO_SERVICO` tem 12 linhas e não encontra chave em `SSO_ASSUNTO` nem no código 156. Forçar o join inventaria uma classificação.
</div>
</div>

<!--
1 minuto e meio.

Tipo de serviço, neste extrato, é o assunto escrito na solicitação: antipó, drenagem, passeio, manutenção corretiva. A tabela TIPO_SERVICO existe, eu ingeri, e ela fica na Silver. São doze descrições genéricas, edificações, pavimentação, sem chave compatível. Publicar um join chute seria pior do que assumir o assunto como proxy e escrever isso.

Região é a unidade regional. Bairro existe, setenta e cinco nomes, e não é o eixo da pergunta.

Solicitação sem execução permanece. Se eu filtrasse só quem tem serviço, o volume de Boa Vista despencaria, e Boa Vista é justamente quem mais pede e menos tem execução lançada neste recorte.
-->

---

## Fontes — espelho C3SL, 21/09/2016

| Tabela | Papel | Silver |
|---|---|---|
| `SERVICO_SOLICITADO` | pedido, regional, assunto, datas, OSO | 50.017 |
| `SERVICO` | execução ligada ao pedido | 337.018 |
| `SERVICO_EXECUTADO` | quantidade e valor do item | 715.973 |
| `SITUACAO_SOLICITACAO` | histórico de situação | 334.548 |
| `GTMBAIBAIRRO` / `TIPO_SERVICO` | dimensões opcionais | 75 / 12 |

`SOLICITACAO 1 ──< SERVICO 1 ──< ITEM`

<!--
2 minutos e meio.

Seis arquivos, todos do mesmo dia no espelho da UFPR. O núcleo obrigatório é solicitação, situação, serviço e item executado. Bairro e tipo de serviço entram porque o enunciado oferece, e porque deixar a dimensão de fora da Bronze esconde a decisão de não usá-la.

O relacionamento que a Gold usa é este: uma solicitação tem vários serviços, um serviço tem vários itens. A situação é histórico. A situação vigente já está na própria solicitação, em SIT_IDF_ATUAL, então o histórico fica disponível na Silver e fora da métrica principal.

Os volumes da Silver já antecipam o problema de integração. Trezentos e trinta e sete mil serviços para cinquenta mil solicitações. A maior parte desses serviços aponta para um SSO_IDF que não está neste recorte.
-->

---

## Qualidade na origem

| Problema | Decisão |
|---|---|
| Delimitador `;`, texto com `;` solto | descarta a linha se a contagem de campos não fecha |
| Latin-1 / cp1252 | decode na Silver; a Bronze guarda o byte original |
| Linha 2 com máscara de tipo | ignorada |
| Byte nulo no meio do texto | removido na Silver; vira nulo |
| Mesma regional em duas caixas | maiúsculas só na Gold |

**Efeito prático:** 3 linhas descartadas no CSV. O estrago não está no parser.

<!--
1 minuto e meio.

O arquivo vem com ponto e vírgula, acentuação em Latin-1, uma segunda linha que é máscara de traços, e em alguns textos um byte nulo. Campo de observação com ponto e vírgula não escapado quebra a contagem de colunas. Essas linhas eu descarto e conto no manifesto. Não reparo na mão.

No recorte inteiro foram três linhas: duas na solicitação, uma no serviço. Duplicidade de chave: zero. O parser não é o risco.

O risco é outro, e eu mostro daqui a pouco: serviço de 2007 apontando para solicitação que não está no extrato de 2016, regional escrita de dois jeitos, e valor de item vazio.
-->

---

## Medalhão, no mesmo contrato do GCP

<div class="flow">
<div class="step"><b>Raw · Bronze</b><span>declaração da fonte e landing fiel. Sem tipo, sem regra.</span></div>
<div class="step"><b>Curated · Silver</b><span>modelo tipado, no grão da origem. Chave, data, nulo, dedup.</span></div>
<div class="step"><b>Consumo · Gold</b><span>fato e agregado. Só aqui existe a pergunta de negócio.</span></div>
</div>

| Na plataforma | Neste repositório |
|---|---|
| Declarações da camada raw | `definitions/sources.yaml` |
| Modelos curated | `jobs/silver.py` → Parquet |
| Modelo de consumo | `jobs/gold.py` |
| DAG Python do orquestrador | `landing_bronze >> curated_silver >> consumo_gold` |
| Bucket de objetos / tabela analítica | SeaweedFS `lake` / Parquet |

<!--
3 minutos. Este é o slide central. Falar devagar.

No GCP a gente separa três responsabilidades, mesmo quando o motor é SQL.

A raw declara a fonte e aterrissa o arquivo. Não interpreta coluna e não aplica regra de negócio. Se o arquivo de origem mudar, a raw muda junto, e a curated é que quebra de forma visível. Aqui isso é o YAML de fontes mais o job de Bronze: URL, recorte, e o CSV byte a byte.

A curated é o modelo limpo, ainda uma linha por registro de origem. Tipo, nulo, chave, deduplicação. É a Silver. Ela não responde "qual regional demora mais". Ela deixa o join possível.

A Gold é consumo. No mesmo fluxo da curated, como último modelo, com outro grão. Fato por solicitação, agregado por regional e assunto. A regra de tempo mora aqui, não na raw.

Quem amarra a ordem é o DAG em Python: landing, curated, consumo. Se a Bronze falha, a Silver não roda. É o mesmo desenho de um pipeline orquestrado: tarefa com dependência, falha visível, reprocessamento da partição.

O que muda neste teste é o runtime, não o contrato. No lugar do bucket gerenciado, SeaweedFS. No lugar da tabela analítica, Parquet. O prefixo bronze, silver, gold e a partição snapshot_date são o contrato do lake.
-->

---

## Contrato do lake e do DAG

```text
lake/bronze/{tabela}/snapshot_date=2016-09-21/data.csv
lake/silver/{tabela}/snapshot_date=2016-09-21/data.parquet
lake/gold/fato_solicitacao_execucao/snapshot_date=2016-09-21/
lake/gold/agregado_regional_assunto/snapshot_date=2016-09-21/
lake/gold/qualidade_integracao/snapshot_date=2016-09-21/
```

Cada prefixo leva `_manifest.json` (origem, extração, sha256 ou contagem) e `_SUCCESS`.

Reexecutar **sobrescreve a mesma chave**.

<!--
1 minuto e meio.

A partição é o dia do recorte, 2016-09-21. Dentro dela, uma tabela por prefixo. Bronze em CSV original. Silver e Gold em Parquet.

O manifesto é a linhagem mínima: de onde veio, quando extraiu, hash na Bronze, linhas descartadas na Silver, grão na Gold. O _SUCCESS marca que a escrita daquele prefixo terminou.

Idempotência é por sobrescrita. A segunda execução, que eu rodei de ponta a ponta, devolveu os mesmos 50.017 pedidos e as mesmas 195 linhas no agregado. Não duplica arquivo e não duplica métrica.

O DAG tem três tarefas com esse nome de propósito: landing_bronze, curated_silver, consumo_gold. Dá para agendar isso sem mudar o job.
-->

---

## Bronze — landing fiel

- Download reproduzível das seis URLs do YAML
- Gravação do conteúdo original em `data.csv`
- Metadado: URL, arquivo, `snapshot_date`, `extracted_at_utc`, bytes, sha256
- Nenhuma coluna é interpretada nesta etapa

<div class="card">
A Silver pode ser reprocessada sem baixar de novo. A Bronze é a fonte interna.
</div>

<!--
1 minuto.

A Bronze não sabe o que é data. Ela sabe de quem baixou e onde guardou. Isso importa quando a regra de tempo muda: eu altero a Gold, ou a Silver, e releio o mesmo CSV.

Os seis arquivos somam cerca de 96 MB. O maior é serviço, 34 MB. O hash no manifesto serve para perceber se o espelho público mudou entre duas extrações do mesmo recorte.
-->

---

## Silver — curated no grão da fonte

- Latin-1, máscara fora, linha desbalanceada fora
- Vazio vira nulo; data inválida vira nulo; decimal com vírgula vira ponto
- Chave natural deduplicada: `SSO_IDF`, `SER_IDF`, `SEE_IDF`
- Texto original da regional **permanece** aqui

| Tabela | Saiu | Descarte de parse |
|---|---:|---:|
| Solicitação | 50.017 | 2 |
| Serviço | 337.018 | 1 |
| Item executado | 715.973 | 0 |
| Situação | 334.548 | 0 |

<!--
2 minutos.

A Silver é o modelo curated: ainda uma linha por registro de negócio, já com tipo.

Eu não corrijo a regional aqui. "Unidade Regional Boa Vista" e "UNIDADE REGIONAL BOA VISTA" são o que o sistema gravou. A conformidade de rótulo, para o indicador, é decisão da Gold. Se alguém quiser auditar o texto original, a Silver ainda tem.

Chave duplicada não apareceu. Chave nula não apareceu. O descarte de parse é residual. Situação não tem chave única de propósito: é histórico, e eu mantenho o histórico inteiro.

O relacionamento ainda não é filtrado. Serviço órfão continua na Silver. Quem decide que órfão não entra no indicador é a Gold, e ela conta o órfão em vez de sumir com ele.
-->

---

## Gold — regras que mudam o número

| Regra | Escolha |
|---|---|
| Grão | 1 solicitação; agregado = regional × assunto |
| Tempo | horas até a **primeira** execução; senão, data de realização |
| Tempo negativo | sai da média e da mediana; fica o flag |
| Valor do item | total informado; senão quantidade × unitário |
| Só unitário, sem quantidade | valor nulo. A quantidade ausente permanece ausente |
| Rótulo | caixa alta na Gold, para unir a mesma regional |
| Órfão | não entra no fato; entra em `qualidade_integracao` |

<!--
2 minutos e meio.

Quatro regras mudam a resposta, então eu falo as quatro.

Primeira: vários serviços na mesma solicitação somam valor e quantidade. A data de execução do pedido é a primeira. Se eu usasse a última, o tempo de atendimento ficaria otimista para quem teve retorno.

Segunda: se a execução está datada antes da abertura, o tempo vai para nulo. São 12.922 casos. Muitos serviços deste arquivo começam em 2007. Usar essa diferença como "tempo de atendimento" publicaria um número negativo ou um número de anos. Quando a execução existe e é inconsistente, eu não troco pela data de realização. O fallback só vale quando não há data de execução.

Terceira: valor. Uso o total do item. Se o total vem vazio e os dois fatores existem, uso o produto. Se só existe o valor unitário, deixo nulo. Inventar quantidade 1 inflaria o valor. Ainda assim, 38.864 itens ligados a solicitações deste recorte ficaram sem valor.

Quarta: a mesma regional vinha em caixa alta e em caixa título. Eram vinte rótulos para dez regionais. A Gold unifica. A Silver não.
-->

---

## Resultado — volume

**50.017 solicitações · 10 regionais · 195 combinações regional × assunto**

| Regional | Pedidos | Sem execução | Mediana |
|---|---:|---:|---:|
| Boa Vista | 10.655 | 88% | 43 dias |
| Matriz | 5.625 | 39% | 9 dias |
| Cajuru | 5.176 | 52% | 10 dias |
| Santa Felicidade | 5.004 | 44% | 14 dias |
| Portão | 4.242 | 43% | 8 dias |
| Bairro Novo | 3.242 | 30% | 7 dias |

Assunto com mais pedidos: **pavimentação alternativa / antipó, 11.374**.

<!--
1 minuto e meio.

Volume. Boa Vista sozinha tem 10.655 pedidos, cerca de um quinto do recorte, e 88% deles não têm execução registrada. O assunto que mais aparece na cidade é pavimentação alternativa, o antipó, com 11.374 solicitações.

A mediana de 43 dias em Boa Vista usa só as durações válidas, cerca de mil casos. Os outros nove mil não entram na conta do tempo. Por isso eu não digo "Boa Vista demora 43 dias" como se fosse a espera de todos os pedidos. Digo: entre os pedidos de Boa Vista que têm data consistente, a mediana é 43 dias, e a maior parte dos pedidos de lá nem chega a ter execução neste extrato.

Matriz é o segundo volume e tem bem mais execução lançada, 39% sem execução, mediana de 9 dias.
-->

---

## Resultado — tempo e valor não são o mesmo conjunto

<div class="grid">
<div class="card">
<h3>Tempo válido</h3>
<div class="num">9.088</div>
de 50.017 pedidos<br>mediana geral: 12 dias
</div>
<div class="card">
<h3>Mais lento, com amostra</h3>
<div class="num">59 dias</div>
Boa Vista · drenagem<br>193 durações válidas
</div>
<div class="card">
<h3>Maior valor</h3>
<div class="num">R$ 7,8 mi</div>
manutenção corretiva<br>só 39 tempos válidos
</div>
</div>

Valor por regional: **Bairro Novo R$ 5,0 mi**, Portão R$ 4,0 mi, Santa Felicidade R$ 2,1 mi.
Boa Vista, líder de volume, tem **R$ 60 mil**.

<!--
1 minuto e meio.

Aqui está a resposta da pergunta, separada de propósito.

Tempo: só 9.088 pedidos têm duração aproveitável. A mediana geral desses é cerca de 12 dias. Onde a amostra segura, o tempo mais longo está na Boa Vista: drenagem, 59 dias de mediana em 193 casos; antipó, 44 dias em 233 casos; limpeza, 47 dias em 313 casos.

Valor: R$ 13,5 milhões executados no recorte. Mais da metade, R$ 7,8 milhões, está em pavimentação de manutenção corretiva. Bairro Novo concentra R$ 5 milhões. Boa Vista, que lidera volume, aparece com R$ 60 mil.

E o detalhe que impede um ranking único: manutenção corretiva tem 5.458 pedidos e só 39 tempos válidos. O valor foi lançado em itens cuja data de execução é anterior à abertura, então o tempo saiu da métrica. Valor alto e tempo longo não descrevem as mesmas linhas.
-->

---

## Limites antes de um indicador oficial

<div class="grid">
<div class="card"><h3>OSO</h3>100% preenchido, só 6 códigos (6, 2, 8, 7, 3, 4). É um código de domínio.</div>
<div class="card"><h3>Órfão</h3>92% dos serviços não acham solicitação neste recorte. 2 itens sem serviço.</div>
<div class="card"><h3>Quantidade</h3>25 milhões somados misturam unidade, m² e trecho. Fica de fora do ranking entre assuntos.</div>
</div>

Indicador oficial de tempo ou de valor precisa, antes, de recorte compatível entre serviço e solicitação e de uma regra de data assinada pelo negócio.

<!--
1 minuto e meio.

Três coisas que o enunciado pedia para olhar e que eu devolvo como limite, não como KPI.

OSO. A pergunta sobre regional com mais pedido sem OSO tem resposta numérica zero: nenhuma linha vem vazia. Só que os valores distintos são seis. Isso não é identificador de ordem de serviço. É um código de domínio, e o dicionário não está no extrato. Publicar "100% com OSO" seria verdadeiro e inútil.

Órfão. 310 mil serviços, 92%, apontam para solicitação que não está nas 50 mil deste arquivo. Dois itens não acham serviço. Isso fica na tabela de qualidade, ao lado da Gold, para não contaminar o fato e também não sumir.

Quantidade. O total de 25 milhões mistura unidade de medida. Eu guardo a coluna e não uso para dizer qual assunto "executou mais".
-->

---

## Reprocessamento

1. `make pipeline` de novo
2. Mesma partição, mesma chave, novo `extracted_at_utc`
3. Contagens idênticas na segunda execução: **50.017** pedidos, **195** linhas no agregado

Falha no meio do DAG interrompe a sequência. O log marca `task start` e `task success`.

Testes do contrato: parser, caminho da partição, soma de vários serviços, pedido sem execução, tempo negativo fora da métrica. **5 testes, no container.**

<!--
1 minuto.

Rodei o pipeline completo duas vezes. A segunda sobrescreveu os objetos e repetiu o quadro de qualidade até o centavo do valor executado.

Os testes não baixam o C3SL. Eles travam o contrato: máscara e linha quebrada, prefixo da partição estável, e as regras da Gold num exemplo pequeno — dois serviços no mesmo pedido somam dezoito, pedido sem execução fica com tempo de dois dias pelo fallback, execução em 2007 com abertura em 2016 não gera tempo.

Se a regra de valor mudar, o teste quebra antes de eu reprocessar os 700 mil itens.
-->

---

## Trade-off e o próximo passo no mesmo desenho

**Agora:** um container, uma partição, Parquet, manifesto, DAG linear.
**Deixei de fora:** scheduler, teste bloqueante, histórico de snapshots, painel.

| Evolução | Onde entra |
|---|---|
| Assertion de chave e de órfão, com limite | modelo curated, antes de publicar a Gold |
| Partição por data de extração | raw, sem sobrescrever o snapshot |
| Tabela externa na Silver, nativa na Gold | consumo |
| Agendar o mesmo DAG | orquestrador |
| Alerta se o cabeçalho do C3SL mudar | raw / contrato da fonte |

<!--
1 minuto e meio.

O trade-off foi profundidade no núcleo, não mais ferramenta. SQL de consumo está em scripts/consulta_gold.sql como contrato da pergunta. A execução é Python porque o runtime daqui é o lake S3, não um warehouse.

O que eu faria em seguida, sem trocar a arquitetura: teste de relacionamento que falha a publicação se o órfão passar de um limite. Hoje ele é contado e a carga segue. Para um indicador oficial, 92% de serviço sem solicitação deveria segurar a Gold.

Depois, partição por extração, para não apagar o snapshot anterior. Tabela externa em cima do Parquet da Silver e tabela nativa para o agregado, que é pequeno, 195 linhas. O DAG que já existe é o que o scheduler chamaria. E um alerta de schema na raw, porque o parser depende da ordem e da contagem de colunas do cabeçalho.

Enriquecer com TIPO_SERVICO só quando existir chave. Até lá, assunto é o tipo.
-->

---

<!-- _class: lead -->

# Volume, tempo e valor não moram juntos

**Volume** em Boa Vista e em antipó.
**Tempo** válido, longo, também em Boa Vista — num subconjunto.
**Valor** em manutenção corretiva, Bairro Novo e Portão, quase sem tempo válido.

A Gold separa essas três leituras. A raw não tenta respondê-las.

<!--
30 segundos de fechamento.

Fecho com a frase que a arquitetura tem que sustentar. Volume, tempo e valor não descrevem o mesmo conjunto de linhas neste recorte. A Gold existe para deixar isso explícito: grão de solicitação, tempo só quando a data é consistente, valor com a regra do item, e uma tabela de qualidade ao lado para o que não entrou.

A raw continua burra de propósito. A regra mora na curated e no consumo. É esse o contrato.

Posso abrir o agregado, o manifesto, ou o teste da duração negativa. Obrigado.
-->
