-- Maior volume
SELECT regional, assunto, volume_solicitacoes, pct_sem_execucao
FROM agregado
ORDER BY volume_solicitacoes DESC
LIMIT 15;

-- Maior tempo mediano, só com amostra
SELECT regional, assunto, tempo_mediano_horas, tempos_validos, volume_solicitacoes
FROM agregado
WHERE tempos_validos >= 30
ORDER BY tempo_mediano_horas DESC
LIMIT 15;

-- Maior valor executado
SELECT regional, assunto, valor_executado, volume_solicitacoes, tempos_validos
FROM agregado
ORDER BY valor_executado DESC NULLS LAST
LIMIT 15;
