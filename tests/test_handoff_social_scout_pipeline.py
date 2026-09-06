# 63.8738, -149.7525

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from models.oferta import Oferta
from services.coletor_ofertas import ColetorOfertas
from services.executor_pipeline import ExecutorPipeline


def criar_oferta(
    *,
    sufixo: str = "1",
    link: str | None = None,
) -> Oferta:
    return Oferta(
        nome=f"Mouse Gamer Modelo Teste {sufixo}",
        loja="Mercado Livre",
        preco=99.90,
        preco_antigo=149.90,
        link=(link or ("https://www.mercadolivre.com.br/" f"produto/p/MLB1234567{sufixo}")),
        imagem=None,
        marketplace="mercado_livre",
        id_produto=f"MLB1234567{sufixo}",
    )


class ScraperHandoffFake:
    def __init__(
        self,
        ofertas,
    ):
        self.ofertas = list(ofertas)
        self.confirmacoes = []

    def buscar_ofertas(
        self,
        limite: int = 5,
    ):
        return list(self.ofertas[:limite])

    def confirmar_handoff(
        self,
        oferta,
        *,
        status,
        motivo,
    ):
        if not any(item is oferta for item in self.ofertas):
            return False

        self.confirmacoes.append(
            (
                oferta,
                status,
                motivo,
            )
        )

        return True


class ValidadorPassaFake:
    def validar(
        self,
        oferta,
        estatisticas=None,
    ):
        oferta.valida = True
        oferta.motivos_validacao = []

        return oferta


class ValidadorRejeitaFake:
    def validar(
        self,
        oferta,
        estatisticas=None,
    ):
        oferta.valida = False
        oferta.motivos_validacao = [
            "invalida_teste",
        ]

        return oferta


class ClassificadorNichoFake:
    def aplicar_classificacao(
        self,
        oferta,
    ):
        return SimpleNamespace(
            eh_nicho=True,
            categoria="perifericos",
            relevancia=90.0,
            motivo="nicho_teste",
        )


class ClassificadorForaFake:
    def aplicar_classificacao(
        self,
        oferta,
    ):
        return SimpleNamespace(
            eh_nicho=False,
            categoria="fora",
            relevancia=0.0,
            motivo="fora_do_nicho",
        )


def test_coletor_confirma_duplicada_removida():
    link = "https://www.mercadolivre.com.br/" "produto/p/MLB12345678"

    primeira = criar_oferta(
        sufixo="1",
        link=link,
    )

    segunda = criar_oferta(
        sufixo="2",
        link=link,
    )

    scraper = ScraperHandoffFake(
        [
            primeira,
            segunda,
        ]
    )

    coletor = ColetorOfertas(
        scrapers=[
            scraper,
        ],
        classificador=ClassificadorNichoFake(),
        validador=ValidadorPassaFake(),
    )

    resultado = coletor.buscar_ofertas(limite_por_scraper=5)

    assert resultado == [
        primeira,
    ]

    assert scraper.confirmacoes == [
        (
            segunda,
            "coletor_duplicada",
            "link_duplicado_no_coletor",
        ),
    ]


def test_coletor_confirma_oferta_invalida():
    oferta = criar_oferta()

    scraper = ScraperHandoffFake(
        [
            oferta,
        ]
    )

    coletor = ColetorOfertas(
        scrapers=[
            scraper,
        ],
        classificador=ClassificadorNichoFake(),
        validador=ValidadorRejeitaFake(),
    )

    assert coletor.buscar_ofertas(limite_por_scraper=5) == []

    assert scraper.confirmacoes == [
        (
            oferta,
            "coletor_rejeitada_validacao",
            "invalida_teste",
        ),
    ]


def test_coletor_confirma_fora_do_nicho():
    oferta = criar_oferta()

    scraper = ScraperHandoffFake(
        [
            oferta,
        ]
    )

    coletor = ColetorOfertas(
        scrapers=[
            scraper,
        ],
        classificador=ClassificadorForaFake(),
        validador=ValidadorPassaFake(),
    )

    assert coletor.buscar_ofertas(limite_por_scraper=5) == []

    assert scraper.confirmacoes == [
        (
            oferta,
            "coletor_fora_nicho",
            "fora_do_nicho",
        ),
    ]


class ColetorExecutorFake:
    def __init__(
        self,
        oferta,
    ):
        self.oferta = oferta
        self.confirmacoes = []

    def buscar_ofertas(
        self,
        limite_por_scraper,
    ):
        return [
            self.oferta,
        ]

    def confirmar_handoffs(
        self,
        ofertas,
        *,
        status,
        motivo,
    ):
        self.confirmacoes.append(
            (
                list(ofertas),
                status,
                motivo,
            )
        )

        return len(ofertas)


class PoliticaBloqueiaFake:
    def analisar(
        self,
        oferta,
    ):
        return SimpleNamespace(
            permitido=False,
            tier="teste",
            motivo="bloqueio_controlado",
        )


class HistoricoFake:
    def salvar_pendentes(
        self,
    ):
        return None


class FilaFake:
    def expirar_antigos(
        self,
        minutos,
    ):
        return 0

    def quantidade_pendente(
        self,
    ):
        return 0

    def reduzir_fila(
        self,
        limite,
    ):
        return 0


class RelatoriosFake:
    def __init__(
        self,
        *,
        falhar=False,
    ):
        self.falhar = falhar
        self.salvos = []

    def salvar(
        self,
        relatorio,
    ):
        if self.falhar:
            raise RuntimeError("falha_relatorio")

        self.salvos.append(relatorio)


def criar_executor(
    *,
    coletor,
    relatorios,
):
    return ExecutorPipeline(
        coletor=coletor,
        repository=object(),
        fila_publicacao_repository=FilaFake(),
        relatorios_repository=relatorios,
        historico_precos_service=HistoricoFake(),
        filtro=object(),
        pontuador=object(),
        quantidade_scrapers=1,
        limite_ofertas=5,
        janela_publicacao=object(),
        detector_anomalia=object(),
        normalizador_produto=object(),
        curadoria_publicacao=object(),
        deduplicacao_canonica_ativa=False,
        fila_reposicao_adaptativa_ativa=False,
        politica_marketplace=PoliticaBloqueiaFake(),
    )


def test_executor_da_ack_depois_do_ciclo():
    oferta = criar_oferta()

    coletor = ColetorExecutorFake(oferta)

    relatorios = RelatoriosFake()

    executor = criar_executor(
        coletor=coletor,
        relatorios=relatorios,
    )

    asyncio.run(executor.executar())

    assert len(relatorios.salvos) == 1

    assert coletor.confirmacoes == [
        (
            [
                oferta,
            ],
            "pipeline_processada",
            ("ciclo_pipeline_" "concluido_com_sucesso"),
        ),
    ]


def test_executor_nao_da_ack_se_ciclo_falhar():
    oferta = criar_oferta()

    coletor = ColetorExecutorFake(oferta)

    executor = criar_executor(
        coletor=coletor,
        relatorios=RelatoriosFake(falhar=True),
    )

    with pytest.raises(
        RuntimeError,
        match="falha_relatorio",
    ):
        asyncio.run(executor.executar())

    assert coletor.confirmacoes == []
