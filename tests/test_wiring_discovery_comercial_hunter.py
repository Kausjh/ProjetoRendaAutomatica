import hashlib
import json
import sqlite3
from datetime import UTC, datetime, timedelta

from services.scout.wiring_discovery_comercial_hunter import (
    aplicar_discovery_comercial_hunter,
)

AGORA = datetime(
    2026,
    9,
    10,
    22,
    30,
    tzinfo=UTC,
)


BASE = {
    "MercadoLivreScraper": 10,
    "ShopeeScraper": 10,
    "KabumScraper": 10,
    "AliExpressScraper": 5,
    "SocialScoutScraper": 5,
}


def _criar_banco(
    caminho,
):
    with sqlite3.connect(caminho) as conexao:

        conexao.execute("""
            CREATE TABLE
            historico_comercial_scout (
                id INTEGER PRIMARY KEY
                    AUTOINCREMENT,
                perfil_json TEXT NOT NULL,
                observado_em TEXT NOT NULL
            )
            """)

        conexao.commit()


def _perfil(
    id_externo: str,
    *,
    marketplace: str = "kabum",
):
    return {
        "fonte": "awin",
        "id_externo": id_externo,
        "marketplace": marketplace,
        "parceiro_id": None,
        "parceiro_nome": None,
        "termos_descoberta": [],
        "codigo_voucher": None,
    }


def _inserir(
    caminho,
    *,
    id_externo: str,
    observado_em: datetime,
    marketplace: str = "kabum",
):
    with sqlite3.connect(caminho) as conexao:

        conexao.execute(
            """
            INSERT INTO
            historico_comercial_scout (
                perfil_json,
                observado_em
            )
            VALUES (?, ?)
            """,
            (
                json.dumps(
                    _perfil(
                        id_externo,
                        marketplace=(marketplace),
                    )
                ),
                observado_em.isoformat(),
            ),
        )

        conexao.commit()


def test_banco_ausente_preserva_base_e_nao_cria_arquivo(
    tmp_path,
):
    caminho = tmp_path / "ausente.sqlite3"

    resultado = aplicar_discovery_comercial_hunter(
        BASE,
        caminho_historico=caminho,
        agora=AGORA,
    )

    assert resultado.como_mapping() == BASE

    assert not caminho.exists()


def test_banco_vazio_preserva_base(
    tmp_path,
):
    caminho = tmp_path / "vazio.sqlite3"

    _criar_banco(caminho)

    resultado = aplicar_discovery_comercial_hunter(
        BASE,
        caminho_historico=caminho,
        agora=AGORA,
    )

    assert resultado.como_mapping() == BASE

    assert resultado.houve_ajuste is False


def test_lote_concentrado_nao_altera_budget(
    tmp_path,
):
    caminho = tmp_path / "concentrado.sqlite3"

    _criar_banco(caminho)

    for indice in range(12):
        _inserir(
            caminho,
            id_externo=(f"lote-{indice}"),
            observado_em=(AGORA - timedelta(minutes=5) + timedelta(milliseconds=(indice * 20))),
        )

    resultado = aplicar_discovery_comercial_hunter(
        BASE,
        caminho_historico=caminho,
        agora=AGORA,
        janela_horas=72,
    )

    assert resultado.como_mapping() == BASE


def test_tendencia_madura_kabum_aumenta_somente_discovery(
    tmp_path,
):
    caminho = tmp_path / "maduro.sqlite3"

    _criar_banco(caminho)

    instantes = (
        AGORA - timedelta(hours=60),
        AGORA - timedelta(hours=50),
        AGORA - timedelta(hours=20),
        AGORA - timedelta(hours=10),
        AGORA - timedelta(hours=5),
    )

    for indice, instante in enumerate(instantes):
        _inserir(
            caminho,
            id_externo=(f"kabum-{indice}"),
            observado_em=instante,
        )

    resultado = aplicar_discovery_comercial_hunter(
        BASE,
        caminho_historico=caminho,
        agora=AGORA,
        janela_horas=72,
    )

    mapping = resultado.como_mapping()

    assert mapping["KabumScraper"] == 15

    assert mapping["MercadoLivreScraper"] == 10

    assert mapping["ShopeeScraper"] == 10

    assert mapping["AliExpressScraper"] == 5

    assert mapping["SocialScoutScraper"] == 5

    assert resultado.fontes_impulsionadas == ("KabumScraper",)


def test_historico_malformado_faz_fail_open(
    tmp_path,
):
    caminho = tmp_path / "malformado.sqlite3"

    _criar_banco(caminho)

    with sqlite3.connect(caminho) as conexao:

        conexao.execute(
            """
            INSERT INTO
            historico_comercial_scout (
                perfil_json,
                observado_em
            )
            VALUES (?, ?)
            """,
            (
                "[]",
                AGORA.isoformat(),
            ),
        )

        conexao.commit()

    resultado = aplicar_discovery_comercial_hunter(
        BASE,
        caminho_historico=caminho,
        agora=AGORA,
    )

    assert resultado.como_mapping() == BASE

    assert resultado.houve_ajuste is False


def test_leitura_nao_modifica_banco(
    tmp_path,
):
    caminho = tmp_path / "readonly.sqlite3"

    _criar_banco(caminho)

    _inserir(
        caminho,
        id_externo="a",
        observado_em=(AGORA - timedelta(hours=60)),
    )

    _inserir(
        caminho,
        id_externo="b",
        observado_em=(AGORA - timedelta(hours=10)),
    )

    antes = hashlib.sha256(caminho.read_bytes()).hexdigest()

    aplicar_discovery_comercial_hunter(
        BASE,
        caminho_historico=caminho,
        agora=AGORA,
    )

    depois = hashlib.sha256(caminho.read_bytes()).hexdigest()

    assert antes == depois
