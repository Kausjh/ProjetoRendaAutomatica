import json
import sqlite3
from datetime import UTC, datetime, timedelta

from services.scout.wiring_alvos_discovery_comercial_hunter import (
    carregar_alvos_discovery_comercial_hunter,
)

AGORA = datetime(
    2026,
    9,
    11,
    15,
    0,
    tzinfo=UTC,
)


def _criar_banco(caminho):
    with sqlite3.connect(caminho) as conexao:
        conexao.execute("""
            CREATE TABLE historico_comercial_scout (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                perfil_json TEXT NOT NULL,
                observado_em TEXT NOT NULL
            )
            """)
        conexao.commit()


def _perfil(
    id_externo: str,
    *,
    termo: str,
):
    return {
        "fonte": "awin",
        "id_externo": id_externo,
        "marketplace": "kabum",
        "parceiro_id": None,
        "parceiro_nome": None,
        "termos_descoberta": [termo],
        "codigo_voucher": None,
        "estrategia_discovery": "buscar_termos_kabum",
        "utilizavel_discovery": True,
    }


def _inserir(
    caminho,
    *,
    id_externo: str,
    observado_em: datetime,
    termo: str,
):
    with sqlite3.connect(caminho) as conexao:
        conexao.execute(
            """
            INSERT INTO historico_comercial_scout (
                perfil_json,
                observado_em
            )
            VALUES (?, ?)
            """,
            (
                json.dumps(
                    _perfil(
                        id_externo,
                        termo=termo,
                    )
                ),
                observado_em.isoformat(),
            ),
        )
        conexao.commit()


def test_banco_ausente_resulta_em_zero_alvos(
    tmp_path,
):
    caminho = tmp_path / "ausente.sqlite3"

    resultado = carregar_alvos_discovery_comercial_hunter(
        caminho_historico=caminho,
        agora=AGORA,
    )

    assert resultado.alvos == ()
    assert not caminho.exists()


def test_rota_kabum_madura_e_carregada_como_alvo(
    tmp_path,
):
    caminho = tmp_path / "maduro.sqlite3"
    termo = "Ryzen 9 9950X3D"

    _criar_banco(caminho)

    instantes = (
        AGORA - timedelta(hours=60),
        AGORA - timedelta(hours=20),
        AGORA - timedelta(hours=5),
    )

    for indice, instante in enumerate(instantes):
        _inserir(
            caminho,
            id_externo=f"kabum-{indice}",
            observado_em=instante,
            termo=termo,
        )

    resultado = carregar_alvos_discovery_comercial_hunter(
        caminho_historico=caminho,
        agora=AGORA,
        janela_horas=72,
    )

    assert resultado.houve_alvos is True
    assert len(resultado.alvos) == 1

    alvo = resultado.alvos[0]

    assert alvo.fonte_hunter == "KabumScraper"
    assert alvo.marketplace == "kabum"
    assert alvo.estrategia == "buscar_termos_kabum"
    assert alvo.termo_busca == termo
    assert alvo.sinais_distintos == 3


def test_historico_malformado_faz_fail_open(
    tmp_path,
):
    caminho = tmp_path / "malformado.sqlite3"

    _criar_banco(caminho)

    with sqlite3.connect(caminho) as conexao:
        conexao.execute(
            """
            INSERT INTO historico_comercial_scout (
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

    resultado = carregar_alvos_discovery_comercial_hunter(
        caminho_historico=caminho,
        agora=AGORA,
    )

    assert resultado.alvos == ()
