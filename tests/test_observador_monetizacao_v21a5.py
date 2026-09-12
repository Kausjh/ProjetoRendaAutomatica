from __future__ import annotations

from datetime import UTC, datetime

from repositories.controle_administrativo_repository import (
    ControleAdministrativoRepository,
)
from services.observador_monetizacao import (
    CHAVE_OBSERVABILIDADE_MONETIZACAO,
    ObservadorMonetizacao,
)


def criar_observador(tmp_path):
    repo = ControleAdministrativoRepository(str(tmp_path / "admin.sqlite3"))
    agora = datetime(
        2026,
        9,
        12,
        16,
        45,
        tzinfo=UTC,
    )
    observador = ObservadorMonetizacao(
        repositorio=repo,
        agora=lambda: agora,
    )
    return observador, repo


def test_observador_persiste_agregados_sem_urls_ou_titulos(
    tmp_path,
):
    observador, repo = criar_observador(tmp_path)

    observador.registrar_processamento(
        link_original=("https://www.mercadolivre.com.br/" "produto/p/MLB123"),
        afiliador="Mercado Livre",
        transformado=True,
        exige_confirmacao=True,
    )

    observador.registrar_processamento(
        link_original=("https://shopee.com.br/" "product/1/2"),
        afiliador="Shopee",
        transformado=False,
        exige_confirmacao=True,
    )

    observador.registrar_retry(
        link_original=("https://shopee.com.br/" "product/1/2"),
        minutos=15,
    )

    snapshot = observador.obter_snapshot()

    assert snapshot["eventos_total"] == 3
    assert snapshot["processamentos_total"] == 2
    assert snapshot["transformados_total"] == 1
    assert snapshot["bloqueios_total"] == 1
    assert snapshot["pass_through_total"] == 0
    assert snapshot["retries_total"] == 1
    assert snapshot["retry_minutos_total"] == 15

    assert snapshot["por_origem"]["mercado_livre"]["transformados"] == 1
    assert snapshot["por_origem"]["shopee"]["bloqueios"] == 1
    assert snapshot["por_origem"]["shopee"]["retries"] == 1

    bruto = repo.obter_estado(CHAVE_OBSERVABILIDADE_MONETIZACAO)

    assert bruto is not None
    assert "MLB123" not in bruto
    assert "product/1/2" not in bruto


def test_observador_reabre_estado_persistido(
    tmp_path,
):
    observador, repo = criar_observador(tmp_path)

    observador.registrar_processamento(
        link_original="https://example.com/a",
        afiliador="Nenhum",
        transformado=False,
        exige_confirmacao=False,
    )

    reaberto = ObservadorMonetizacao(
        repositorio=repo,
        agora=lambda: datetime(
            2026,
            9,
            12,
            17,
            0,
            tzinfo=UTC,
        ),
    )

    snapshot = reaberto.obter_snapshot()

    assert snapshot["processamentos_total"] == 1
    assert snapshot["pass_through_total"] == 1
    assert snapshot["por_origem"]["outro"]["pass_through"] == 1


def test_observador_normaliza_afiliador_sem_expor_nome_cru(
    tmp_path,
):
    observador, _repo = criar_observador(tmp_path)

    observador.registrar_processamento(
        link_original="https://example.com/a",
        afiliador="  Awin Parceiro BR  ",
        transformado=True,
        exige_confirmacao=False,
    )

    snapshot = observador.obter_snapshot()

    assert "awin_parceiro_br" in (snapshot["por_afiliador"])
