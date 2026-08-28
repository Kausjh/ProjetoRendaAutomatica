from types import SimpleNamespace

import pytest

from services.historico_precos_service import (
    HistoricoPrecosService,
)


class RepositorioFake:
    def __init__(self) -> None:
        self.salvamentos = 0

    def obter_registros(self, chave_produto):
        return []

    def registrar_preco(self, **kwargs):
        return True

    def salvar(self) -> None:
        self.salvamentos += 1


def criar_oferta(indice: int):
    return SimpleNamespace(
        id_produto=f"produto-{indice}",
        id_anuncio=None,
        link=f"https://example.com/{indice}",
        nome=f"Produto {indice}",
        categoria="Teste",
        preco=100.0 + indice,
    )


def test_historico_salva_em_lotes_e_faz_flush_final() -> None:
    repository = RepositorioFake()

    service = HistoricoPrecosService(
        repository=repository,
        tamanho_lote_salvamento=3,
    )

    service.analisar_e_registrar(criar_oferta(1))
    service.analisar_e_registrar(criar_oferta(2))

    assert repository.salvamentos == 0

    service.analisar_e_registrar(criar_oferta(3))

    assert repository.salvamentos == 1

    service.analisar_e_registrar(criar_oferta(4))

    assert repository.salvamentos == 1

    service.salvar_pendentes()

    assert repository.salvamentos == 2

    service.salvar_pendentes()

    assert repository.salvamentos == 2


def test_historico_rejeita_tamanho_de_lote_invalido() -> None:
    with pytest.raises(ValueError):
        HistoricoPrecosService(
            repository=RepositorioFake(),
            tamanho_lote_salvamento=0,
        )
