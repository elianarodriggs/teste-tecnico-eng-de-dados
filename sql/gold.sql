-- Fato no grão da solicitação.
-- Itens são somados por serviço, e serviços por solicitação, antes do join.
-- Valor e quantidade ausentes permanecem nulos. Zero só aparece se a soma for zero.

CREATE OR REPLACE TABLE item_por_servico AS
SELECT
    SER_IDF,
    COUNT(*) AS qtd_itens,
    SUM(SEE_QUANTIDADE) AS quantidade_executada,
    SUM(
        COALESCE(
            SEE_VALOR_TOTAL,
            CASE
                WHEN SEE_QUANTIDADE IS NOT NULL AND SEE_VALOR_UNIDADE IS NOT NULL
                THEN SEE_QUANTIDADE * SEE_VALOR_UNIDADE
                ELSE NULL
            END
        )
    ) AS valor_executado,
    SUM(
        CASE
            WHEN SEE_VALOR_TOTAL IS NULL
             AND (SEE_QUANTIDADE IS NULL OR SEE_VALOR_UNIDADE IS NULL)
            THEN 1 ELSE 0
        END
    ) AS itens_sem_valor
FROM servico_executado
GROUP BY SER_IDF;

CREATE OR REPLACE TABLE servico_por_solicitacao AS
SELECT
    s.SSO_IDF,
    COUNT(DISTINCT s.SER_IDF) AS qtd_servicos,
    MIN(s.SER_DATA_EXECUCAO) AS primeira_execucao,
    MAX(s.SER_DATA_EXECUCAO) AS ultima_execucao,
    SUM(i.qtd_itens) AS qtd_itens,
    SUM(i.quantidade_executada) AS quantidade_executada,
    SUM(i.valor_executado) AS valor_executado,
    SUM(i.itens_sem_valor) AS itens_sem_valor
FROM servico s
LEFT JOIN item_por_servico i ON s.SER_IDF = i.SER_IDF
WHERE s.SSO_IDF IS NOT NULL
GROUP BY s.SSO_IDF;

CREATE OR REPLACE TABLE fato AS
SELECT
    o.SSO_IDF,
    o.regional,
    o.assunto,
    o.SSO_REGIONAL AS regional_original,
    o.SSO_ASSUNTO AS assunto_original,
    o.SSO_DATA_SOLICITACAO AS data_abertura,
    o.SSO_DATA_REALIZACAO AS data_realizacao,
    e.primeira_execucao,
    e.ultima_execucao,
    COALESCE(e.qtd_servicos, 0) AS qtd_servicos,
    e.qtd_itens,
    e.quantidade_executada,
    e.valor_executado,
    COALESCE(e.itens_sem_valor, 0) AS itens_sem_valor,
    CASE WHEN e.SSO_IDF IS NULL THEN 0 ELSE 1 END AS possui_execucao,
    CASE
        WHEN e.primeira_execucao IS NOT NULL
         AND o.SSO_DATA_SOLICITACAO IS NOT NULL
         AND e.primeira_execucao < o.SSO_DATA_SOLICITACAO
        THEN 1
        WHEN e.primeira_execucao IS NULL
         AND o.SSO_DATA_REALIZACAO IS NOT NULL
         AND o.SSO_DATA_SOLICITACAO IS NOT NULL
         AND o.SSO_DATA_REALIZACAO < o.SSO_DATA_SOLICITACAO
        THEN 1
        ELSE 0
    END AS tempo_negativo,
    CASE
        WHEN e.primeira_execucao IS NOT NULL
         AND o.SSO_DATA_SOLICITACAO IS NOT NULL
         AND e.primeira_execucao >= o.SSO_DATA_SOLICITACAO
        THEN date_diff('minute', o.SSO_DATA_SOLICITACAO, e.primeira_execucao) / 60.0
        WHEN e.primeira_execucao IS NULL
         AND o.SSO_DATA_REALIZACAO IS NOT NULL
         AND o.SSO_DATA_SOLICITACAO IS NOT NULL
         AND o.SSO_DATA_REALIZACAO >= o.SSO_DATA_SOLICITACAO
        THEN date_diff('minute', o.SSO_DATA_SOLICITACAO, o.SSO_DATA_REALIZACAO) / 60.0
        ELSE NULL
    END AS tempo_horas,
    o.OSO_IDF,
    o.SIT_IDF_ATUAL
FROM servico_solicitado o
LEFT JOIN servico_por_solicitacao e ON o.SSO_IDF = e.SSO_IDF;

CREATE OR REPLACE TABLE agregado AS
SELECT
    regional,
    assunto,
    COUNT(DISTINCT SSO_IDF) AS volume_solicitacoes,
    SUM(possui_execucao) AS solicitacoes_com_execucao,
    COUNT(*) - SUM(possui_execucao) AS solicitacoes_sem_execucao,
    (COUNT(*) - SUM(possui_execucao)) * 1.0 / COUNT(*) AS pct_sem_execucao,
    AVG(tempo_horas) AS tempo_medio_horas,
    MEDIAN(tempo_horas) AS tempo_mediano_horas,
    COUNT(tempo_horas) AS tempos_validos,
    SUM(tempo_negativo) AS tempos_negativos,
    SUM(quantidade_executada) AS quantidade_executada,
    SUM(valor_executado) AS valor_executado
FROM fato
GROUP BY regional, assunto
ORDER BY volume_solicitacoes DESC, valor_executado DESC NULLS LAST;
