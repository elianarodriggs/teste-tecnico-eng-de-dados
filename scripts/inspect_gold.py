from lago import Lago

lago = Lago()
quando = lago.data_extracao
agregado = lago.ler_parquet(f"gold/agregado_regional_assunto/extraction_date={quando}/data.parquet")
validacao = lago.ler_parquet(f"gold/validacao/extraction_date={quando}/data.parquet")
print("extracao", quando)
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
