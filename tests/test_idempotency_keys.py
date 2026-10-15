from sigmu_pipeline.config import object_prefix


def test_prefixo_de_particao_e_estavel():
    assert object_prefix("bronze", "servico_solicitado", "2016-09-21") == (
        "bronze/servico_solicitado/snapshot_date=2016-09-21"
    )
    assert object_prefix("gold", "agregado_regional_assunto", "2016-09-21").endswith(
        "snapshot_date=2016-09-21"
    )
