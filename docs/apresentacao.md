---
marp: true
theme: default
paginate: true
size: 16:9
title: Pipeline SIGMU
---

<!-- _class: lead -->

# Pipeline SIGMU
## Manutenção urbana de Curitiba

Quais regiões e tipos de pedido concentram volume, tempo e valor?

Recorte de 21/09/2016 · defesa de cerca de 20 minutos

---

## Roteiro

| Bloco | Tempo |
|---|---|
| Problema e objetivo | 2 min |
| Fontes e qualidade | 3 min |
| Arquitetura | 3 min |
| Modelo e transformações | 4 min |
| Resultados reais | 4 min |
| Testes e próximos passos | 4 min |

---

## Fontes e o que a leitura encontrou

Núcleo: solicitação, situação, serviço e item executado. Bairro e tipo de serviço também entraram.

| Problema | O que foi feito |
|---|---|
| `;`, Latin-1, linha de máscara | máscara ignorada; bytes originais ficam na Bronze |
| Campo com `;` solto | 3 linhas foram para quarentena |
| Chave e duplicidade | nenhuma chave nula e nenhuma duplicata |

`SERVICO.SSO_IDF` liga no pedido. `SERVICO_EXECUTADO.SER_IDF` liga no serviço. Situação é histórico, não domínio.

---

## Arquitetura

```text
C3SL  ->  bronze  ->  silver  ->  gold
CSV         original    Parquet     1 linha por solicitação
```

| Peça | Função |
|---|---|
| SeaweedFS | bucket `lake`, compatível com S3 |
| `src/main.py` | sobe bronze, silver e gold |
| `src/lago.py` | grava e lê o SeaweedFS |
| `sql/gold.sql` | DuckDB monta o fato e o agregado |
| Docker | o pipeline roda no container |

A partição é `extraction_date`, o dia da carga. O período do arquivo continua `2016-09-21`.

---

## Regras que mudam o número

- Grão: **1 solicitação**. O assunto está no pedido.
- Vários serviços: soma de quantidade e valor, primeira data de execução.
- Sem serviço ligado: a solicitação permanece, com `possui_execucao = 0`.
- Tempo negativo: sai da média e da mediana.
- Valor ausente continua nulo. Não vira zero.
- Tipo da dimensão `TIPO_SERVICO` não tem chave. O tipo usado é `SSO_ASSUNTO`.

A carga para se a Gold tiver mais linhas do que solicitações na Silver.

---

## Resultado — volume

**50.017 solicitações. A Gold tem as mesmas 50.017.**

| Regional | Pedidos | Sem serviço |
|---|---:|---:|
| Boa Vista | 10.655 | 88% |
| Matriz | 5.625 | 39% |
| Cajuru | 5.176 | 52% |
| Santa Felicidade | 5.004 | 44% |
| Bairro Novo | 3.242 | 30% |

Assunto com mais pedidos: **pavimentação alternativa / antipó, 11.374**.

---

## Resultado — tempo e valor

<div class="grid">
<div class="card"><h3>Tempo válido</h3>9.088 de 50.017<br>12.922 tempos negativos ficaram de fora</div>
<div class="card"><h3>Mais lento</h3>Boa Vista · drenagem<br>mediana de cerca de 59 dias<br>193 tempos válidos</div>
<div class="card"><h3>Maior valor</h3>R$ 7,8 mi<br>manutenção corretiva<br>só 39 tempos válidos</div>
</div>

Valor por regional: Bairro Novo R$ 5,0 mi, Portão R$ 4,0 mi. Boa Vista, líder de volume, tem R$ 60 mil.

**310 mil serviços (92%)** apontam para um pedido que não está neste arquivo. Ficam de fora do fato e entram na validação.

---

## Testes, reexecução e o que ficou de fora

O pipeline foi executado de ponta a ponta. A mesma `extraction_date` é sobrescrita, então a segunda rodada não duplica.

Os testes verificam a quarentena, a soma de vários serviços e o tempo negativo.

Antes de um indicador oficial:

- investigar o desencontro entre serviço e solicitação;
- não usar `OSO_IDF` como número de ordem: só há seis códigos e nenhum nulo;
- não somar quantidade entre assuntos, porque a unidade muda.

Próximo passo: falhar a publicação se o órfão passar de um limite, e guardar mais de uma data de extração.
