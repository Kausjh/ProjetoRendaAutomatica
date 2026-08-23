from bot_consulta import (
    contem_palavra,
    normalizar_busca,
    separar_comparacao,
)


def test_busca_exata_nao_confunde_5700x_com_5700x3d():
    titulo = normalizar_busca("AMD Ryzen 7 5700X3D")

    assert not contem_palavra(titulo, "5700x")
    assert contem_palavra(titulo, "5700x3d")


def test_alias_r7_expande_para_ryzen_7():
    assert normalizar_busca("r7 5700x") == "ryzen 7 5700x"


def test_alias_r5_expande_para_ryzen_5():
    assert normalizar_busca("r5 5600") == "ryzen 5 5600"


def test_separar_comparacao_com_vs():
    assert separar_comparacao("rtx 4060 vs rx 7600") == (
        "rtx 4060",
        "rx 7600",
    )


def test_separar_comparacao_com_versus():
    assert separar_comparacao("5700x versus 5700x3d") == (
        "5700x",
        "5700x3d",
    )


def test_texto_normal_nao_vira_comparacao():
    assert separar_comparacao("monitor gamer 144hz") is None
