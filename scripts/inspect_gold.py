# Lê a Gold de hoje no SeaweedFS e imprime o ranking.

from storage import extraction_date, read_parquet

when = extraction_date()
agregado = read_parquet(f"gold/agregado_regional_assunto/extraction_date={when}/data.parquet")
validacao = read_parquet(f"gold/validacao/extraction_date={when}/data.parquet")
print("extracao", when)
print(validacao.T.to_string(header=False))
print()
colunas = [
    "regional",
    "assunto",
    "volume_solicitacoes",
    "tempos_validos",
    "tempo_mediano_horas",
    "valor_executado",
    "pct_sem_execucao",
]
print(agregado[colunas].head(12).to_string(index=False))
print()
print(agregado.sort_values("valor_executado", ascending=False)[colunas].head(8).to_string(index=False))
