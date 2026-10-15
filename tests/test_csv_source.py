from sigmu_pipeline.csv_source import parse_sigmu_csv


def test_ignora_mascara_e_descarta_delimitador_quebrado():
    raw = (
        "SSO_IDF;SSO_ASSUNTO;SSO_DESCRICAO\n"
        "-------;-----------;-------------\n"
        "1;PASSEIO;texto ok\n"
        "2;PAVIMENTAÇÃO;campo;com;ponto e virgula extra\n"
        "\n"
        "3;ILUMINAÇÃO;outro\n"
    ).encode("latin-1")

    frame, dropped = parse_sigmu_csv(raw)

    assert dropped == 2
    assert list(frame["SSO_IDF"]) == ["1", "3"]
    assert frame.iloc[0]["SSO_ASSUNTO"] == "PASSEIO"


def test_remove_byte_nulo_e_preserva_acento():
    raw = "SER_IDF;SER_OBSERVACAO\n-------;--------------\n2;rua\x00 do centro\n".encode("latin-1")
    frame, dropped = parse_sigmu_csv(raw)
    assert dropped == 0
    assert frame.iloc[0]["SER_OBSERVACAO"] == "rua do centro"
