from datetime import UTC, datetime, timedelta

import pytest

from models.perfil_comercial_scout import (
    PerfilComercialScout,
)
from repositories.historico_comercial_scout_repository import (
    HistoricoComercialScoutRepository,
)
from services.scout.historico_comercial_scout import (
    HistoricoComercialScout,
)

AGORA = datetime(
    2026,
    9,
    10,
    18,
    0,
    tzinfo=UTC,
)


def criar_perfil(
    id_externo="1",
    **alteracoes,
):
    dados = {
        "fonte": "awin",
        "id_externo": id_externo,
        "tipo_sinal": "promotion",
        "titulo": "Campanha Gamer",
        "marketplace": "kabum",
        "tipo_destino": "campanha",
        "parceiro_id": "123",
        "parceiro_nome": "Kabum BR",
        "codigo_voucher": "GAMER10",
        "inicio": "2026-09-10",
        "fim": "2026-09-12",
        "regioes": ("BR",),
        "estrategia_discovery": ("buscar_termos_kabum"),
        "termos_descoberta": ("Ryzen",),
        "dimensoes": (
            "campanha",
            "cupom",
            "parceiro",
        ),
        "evidencias": (
            "tipo_comercial",
            "voucher_explicito",
        ),
        "landing_page": True,
        "utilizavel_discovery": True,
    }

    dados.update(alteracoes)

    return PerfilComercialScout(**dados)


def criar_repository(
    tmp_path,
):
    return HistoricoComercialScoutRepository(tmp_path / "historico_comercial.sqlite3")


def test_repository_registra_observacao(
    tmp_path,
):
    repository = criar_repository(tmp_path)

    identificador = repository.registrar(
        perfil=criar_perfil(),
        tipo_evento="novo",
        observado_em=AGORA,
    )

    assert identificador == 1
    assert repository.quantidade() == 1


def test_repository_reconstroi_perfil_com_tuplas(
    tmp_path,
):
    repository = criar_repository(tmp_path)

    perfil = criar_perfil()

    repository.registrar(
        perfil=perfil,
        tipo_evento="novo",
        observado_em=AGORA,
    )

    observacoes = repository.listar_observacoes()

    assert len(observacoes) == 1

    reconstruido = observacoes[0].perfil

    assert reconstruido == perfil

    assert isinstance(
        reconstruido.regioes,
        tuple,
    )

    assert isinstance(
        reconstruido.termos_descoberta,
        tuple,
    )


def test_repository_normaliza_timezone_para_utc(
    tmp_path,
):
    repository = criar_repository(tmp_path)

    horario = datetime.fromisoformat("2026-09-10T15:00:00-03:00")

    repository.registrar(
        perfil=criar_perfil(),
        tipo_evento="novo",
        observado_em=horario,
    )

    observacao = repository.listar_observacoes()[0]

    assert observacao.observado_em == AGORA


def test_repository_rejeita_datetime_sem_timezone(
    tmp_path,
):
    repository = criar_repository(tmp_path)

    with pytest.raises(
        ValueError,
        match="timezone",
    ):
        repository.registrar(
            perfil=criar_perfil(),
            tipo_evento="novo",
            observado_em=datetime(
                2026,
                9,
                10,
                18,
                0,
            ),
        )


def test_historico_registra_evento_novo(
    tmp_path,
):
    repository = criar_repository(tmp_path)

    historico = HistoricoComercialScout(repository)

    registrado = historico.registrar(
        perfil=criar_perfil(),
        tipo_evento="novo",
        observado_em=AGORA,
    )

    assert registrado is True
    assert repository.quantidade() == 1


def test_historico_registra_evento_atualizado(
    tmp_path,
):
    repository = criar_repository(tmp_path)

    historico = HistoricoComercialScout(repository)

    registrado = historico.registrar(
        perfil=criar_perfil(),
        tipo_evento="atualizado",
        observado_em=AGORA,
    )

    assert registrado is True
    assert repository.quantidade() == 1


def test_historico_nao_registra_inalterado(
    tmp_path,
):
    repository = criar_repository(tmp_path)

    historico = HistoricoComercialScout(repository)

    registrado = historico.registrar(
        perfil=criar_perfil(),
        tipo_evento="inalterado",
        observado_em=AGORA,
    )

    assert registrado is False
    assert repository.quantidade() == 0


def test_historico_rejeita_evento_desconhecido(
    tmp_path,
):
    repository = criar_repository(tmp_path)

    historico = HistoricoComercialScout(repository)

    with pytest.raises(
        ValueError,
        match="tipo_evento",
    ):
        historico.registrar(
            perfil=criar_perfil(),
            tipo_evento="qualquer_coisa",
            observado_em=AGORA,
        )


def test_observacoes_recentes_respeitam_janela(
    tmp_path,
):
    repository = criar_repository(tmp_path)

    historico = HistoricoComercialScout(repository)

    repository.registrar(
        perfil=criar_perfil("antigo"),
        tipo_evento="novo",
        observado_em=(AGORA - timedelta(hours=100)),
    )

    repository.registrar(
        perfil=criar_perfil("recente"),
        tipo_evento="novo",
        observado_em=(AGORA - timedelta(hours=10)),
    )

    observacoes = historico.observacoes_recentes(
        janela_horas=72,
        agora=AGORA,
    )

    assert len(observacoes) == 1

    assert observacoes[0].perfil.id_externo == "recente"


def test_mesmo_sinal_pode_ter_eventos_em_momentos_distintos(
    tmp_path,
):
    repository = criar_repository(tmp_path)

    perfil = criar_perfil("mesmo")

    repository.registrar(
        perfil=perfil,
        tipo_evento="novo",
        observado_em=(AGORA - timedelta(hours=24)),
    )

    repository.registrar(
        perfil=perfil,
        tipo_evento="atualizado",
        observado_em=AGORA,
    )

    observacoes = repository.listar_observacoes()

    assert len(observacoes) == 2

    assert {item.perfil.id_externo for item in observacoes} == {
        "mesmo",
    }
