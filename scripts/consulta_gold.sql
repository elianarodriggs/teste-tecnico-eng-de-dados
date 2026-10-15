-- Consulta de consumo da Gold.
-- Grão: uma linha por regional e assunto.
-- Tipo de serviço da pergunta = assunto da solicitação (SSO_ASSUNTO),
-- já normalizado em maiúsculas na Gold.
-- tempo_* ignora duração negativa; use tempo_amostras antes de rankear tempo.

SELECT
    regional,
    assunto,
    volume_solicitacoes,
    tempo_amostras,
    tempo_medio_horas,
    tempo_mediano_horas,
    valor_total_executado,
    pct_sem_oso,
    pct_sem_execucao
FROM agregado_regional_assunto
ORDER BY volume_solicitacoes DESC, valor_total_executado DESC
LIMIT 20;
