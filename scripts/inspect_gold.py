"""Mostra o ranking da Gold e o quadro de integração."""

from __future__ import annotations

from sigmu_pipeline.config import load_config, object_prefix
from sigmu_pipeline.io import read_parquet


def main() -> None:
    cfg = load_config()
    snapshot = cfg.snapshot_date
    agregado = read_parquet(
        cfg.s3, f"{object_prefix('gold', 'agregado_regional_assunto', snapshot)}/data.parquet"
    )
    qualidade = read_parquet(
        cfg.s3, f"{object_prefix('gold', 'qualidade_integracao', snapshot)}/data.parquet"
    )

    print("=== qualidade de integração ===")
    print(qualidade.T.to_string(header=False))
    print()
    colunas = [
        "regional",
        "assunto",
        "volume_solicitacoes",
        "tempo_amostras",
        "tempo_mediano_horas",
        "valor_total_executado",
        "pct_sem_execucao",
        "pct_sem_oso",
    ]
    print("=== maior volume (regional x assunto) ===")
    print(agregado[colunas].head(15).to_string(index=False))
    print()
    print("=== maior valor executado ===")
    por_valor = agregado.sort_values("valor_total_executado", ascending=False)
    print(por_valor[colunas].head(10).to_string(index=False))
    print()
    print("=== maior tempo mediano (com pelo menos 30 durações válidas) ===")
    relevantes = agregado[agregado["tempo_amostras"] >= 30].sort_values(
        "tempo_mediano_horas", ascending=False
    )
    print(relevantes[colunas].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
