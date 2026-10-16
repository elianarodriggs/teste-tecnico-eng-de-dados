# Solução — Pipeline SIGMU

O pipeline baixa o recorte público do SIGMU, guarda o arquivo original e produz uma visão por regional e assunto. A pergunta é: quais tipos de serviço e regiões concentram maior volume, maior tempo de atendimento e maior valor executado.

```text
C3SL  CSV 2016-09-21
        |
        v
     bronze     arquivo original + manifesto
        |
        v
     silver     Parquet tipado + quarentena
        |
        v
      gold      1 linha por solicitação
                agregado regional × assunto
```

```text
SERVICO_SOLICITADO 1 ──< N SERVICO 1 ──< N SERVICO_EXECUTADO
```

## Como executar

Na raiz do repositório. Nesta máquina os comandos Docker usam `sudo`.

```bash
cp .env.example .env
sudo docker compose up -d
sudo docker compose --profile pipeline run --rm pipeline all
sudo docker compose --profile pipeline run --rm --no-deps --entrypoint python pipeline /app/scripts/inspect_gold.py
```

Testes:

```bash
sudo docker compose --profile pipeline run --rm --entrypoint pytest pipeline -q
```

S3: `http://localhost:8333`. Filer: `http://localhost:8888`. Master: `http://localhost:9333`.

O serviço `pipeline` fala com o storage em `http://seaweedfs:8333`, porque `localhost` dentro do container não é a máquina. O build usa `--trusted-host` e monta o bundle de CAs desta rede. O relógio do container é `America/Sao_Paulo`.

## Onde estão os dados

Bucket `lake`. A partição é a data da execução, não o período do arquivo.

| Camada | Caminho |
|---|---|
| Bronze | `bronze/{tabela}/extraction_date=AAAA-MM-DD/{nome original}.csv` |
| Silver | `silver/{tabela}/extraction_date=AAAA-MM-DD/data.parquet` |
| Qualidade | `silver/_quality/extraction_date=AAAA-MM-DD/metrics.parquet` e `quarentena.parquet` |
| Gold | `gold/fato_solicitacao/.../data.parquet` |
| Gold | `gold/agregado_regional_assunto/.../data.parquet` |

O manifesto de cada objeto traz URL, data de extração, período do dataset (`2016-09-21`), tamanho e sha256.

Nesta execução a extração ficou em `extraction_date=2026-10-15`. Uma carga anterior, com o relógio do container em UTC, deixou a partição `2026-10-16`. Os totais de negócio das duas são os mesmos. A de `2026-10-15` também trouxe `tipo_servico` (12 linhas).

## Resultado

A Gold tem 50.017 solicitações, o mesmo total da Silver. O join não duplicou pedido.

- Volume: Boa Vista, 10.655 pedidos (88% sem serviço ligado). Assunto mais frequente: pavimentação alternativa / antipó, 11.374.
- Tempo: 9.088 durações válidas. A mediana mais longa com amostra está em drenagem na Boa Vista, cerca de 59 dias.
- Valor: R$ 13,5 milhões. Manutenção corretiva de pavimentação concentra R$ 7,8 milhões, sobretudo Bairro Novo e Portão. Nesse grupo quase não há tempo válido.

As consultas estão em `sql/consultas.sql`. A apresentação está em `docs/apresentacao.pdf`.

## Reexecução

Rodar de novo no mesmo dia sobrescreve a mesma chave `extraction_date`. Não acumula linha nem arquivo. Duas execuções em `2026-10-15` devolveram os mesmos totais e o mesmo sha256 de cada CSV. Uma etapa obrigatória que falha interrompe as seguintes.

## Limitações

- 92% dos serviços não encontram solicitação neste recorte. O fato não os inclui. A contagem está na validação da Gold.
- `TIPO_SERVICO` não tem chave para o pedido. O tipo usado é `SSO_ASSUNTO`.
- Quantidade soma unidades diferentes e não entra no ranking.
- `SITUACAO_SOLICITACAO` é histórico e não entra na métrica. `SIT_IDF_ATUAL` fica no fato.
- `OSO_IDF` está preenchido em todas as linhas e só tem seis códigos.

## Próximos passos

- Segurar a Gold se o percentual de serviço sem solicitação passar de um limite.
- Guardar o histórico de extrações em vez de olhar só o dia corrente.
- Painel sobre `agregado_regional_assunto`.

As regras estão em `docs/decisoes.md`.
