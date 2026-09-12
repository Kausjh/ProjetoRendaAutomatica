from __future__ import annotations

from pathlib import Path

from models.oferta import Oferta
from repositories.catalogo_canonico_repository import (
    CatalogoCanonicoRepository,
)
from services.catalogo_canonico_service import (
    CatalogoCanonicoService,
)


def oferta(
    *,
    marketplace: str = "mercado_livre",
    id_anuncio: str | None = "MLB123",
    id_produto: str | None = "MLB123",
    chave: str = "rtx_4060",
    nome_canonico: str = "RTX 4060",
    confianca: float = 95.0,
    link: str = "https://example.com/produto",
) -> Oferta:
    item = Oferta(
        nome="Oferta de teste",
        loja=marketplace,
        preco=1000.0,
        preco_antigo=None,
        link=link,
        imagem=None,
        marketplace=marketplace,
        id_anuncio=id_anuncio,
        id_produto=id_produto,
    )
    item.categoria = "Placa de video"
    item.marca = "Teste"
    item.produto_canonico = nome_canonico
    item.chave_produto_canonica = chave
    item.modelo_produto = nome_canonico
    item.confianca_normalizacao = confianca
    return item


def criar(tmp_path):
    repository = CatalogoCanonicoRepository(tmp_path / "catalogo.sqlite3")
    service = CatalogoCanonicoService(repository)
    return repository, service


def test_mesmo_produto_reune_anuncios_de_marketplaces_diferentes(
    tmp_path,
):
    repository, service = criar(tmp_path)

    ml = oferta(
        marketplace="mercado_livre",
        id_anuncio="MLB1",
        id_produto="MLB1",
    )
    shopee = oferta(
        marketplace="shopee",
        id_anuncio="SHOPEE2",
        id_produto="SHOPEE2",
    )

    assert service.observar(ml).registrado is True
    assert service.observar(shopee).registrado is True

    produto = repository.obter_produto("rtx_4060")

    assert produto is not None
    assert repository.quantidade_produtos() == 1
    assert repository.quantidade_anuncios() == 2
    assert {anuncio.marketplace for anuncio in produto.anuncios} == {"mercado_livre", "shopee"}


def test_catalogo_persiste_entre_instancias(tmp_path):
    caminho = tmp_path / "catalogo.sqlite3"

    repository = CatalogoCanonicoRepository(caminho)
    service = CatalogoCanonicoService(repository)

    assert service.observar(oferta()).registrado is True

    reaberto = CatalogoCanonicoRepository(caminho)
    produto = reaberto.obter_produto("rtx_4060")

    assert produto is not None
    assert produto.nome_canonico == "RTX 4060"
    assert len(produto.anuncios) == 1


def test_baixa_confianca_nao_entra_no_catalogo(tmp_path):
    repository, service = criar(tmp_path)

    resultado = service.observar(oferta(confianca=45.0))

    assert resultado.registrado is False
    assert resultado.status == "ignorado_baixa_confianca"
    assert repository.quantidade_produtos() == 0
    assert repository.quantidade_anuncios() == 0


def test_sem_id_nao_faz_merge_por_url(tmp_path):
    repository, service = criar(tmp_path)

    resultado = service.observar(
        oferta(
            id_anuncio=None,
            id_produto=None,
        )
    )

    assert resultado.registrado is False
    assert resultado.status == "ignorado_sem_identificador_anuncio"
    assert repository.quantidade_produtos() == 0


def test_mesmo_anuncio_nao_pode_ser_remapeado_automaticamente(
    tmp_path,
):
    repository, service = criar(tmp_path)

    original = oferta(
        chave="rtx_4060",
        nome_canonico="RTX 4060",
    )
    conflitante = oferta(
        chave="rtx_4070",
        nome_canonico="RTX 4070",
    )

    assert service.observar(original).registrado is True

    resultado = service.observar(conflitante)

    assert resultado.registrado is False
    assert resultado.status == "conflito_anuncio"

    produto = repository.obter_por_anuncio(
        marketplace="mercado_livre",
        identificador="MLB123",
    )

    assert produto is not None
    assert produto.chave_canonica == "rtx_4060"
    assert repository.obter_produto("rtx_4070") is None


def test_reobservacao_do_mesmo_anuncio_e_idempotente(tmp_path):
    repository, service = criar(tmp_path)

    primeira = oferta(link="https://example.com/a")
    segunda = oferta(link="https://example.com/b")

    assert service.observar(primeira).registrado is True
    assert service.observar(segunda).registrado is True

    assert repository.quantidade_produtos() == 1
    assert repository.quantidade_anuncios() == 1

    produto = repository.obter_produto("rtx_4060")

    assert produto is not None
    assert produto.anuncios[0].link == "https://example.com/b"


def test_id_anuncio_tem_precedencia_sobre_id_produto(tmp_path):
    repository, service = criar(tmp_path)

    item = oferta(
        id_anuncio="ANUNCIO-1",
        id_produto="PRODUTO-9",
    )

    resultado = service.observar(item)

    assert resultado.identificador_anuncio == "ANUNCIO-1"

    assert (
        repository.obter_por_anuncio(
            marketplace="mercado_livre",
            identificador="ANUNCIO-1",
        )
        is not None
    )

    assert (
        repository.obter_por_anuncio(
            marketplace="mercado_livre",
            identificador="PRODUTO-9",
        )
        is None
    )


def test_pipeline_observa_catalogo_depois_da_normalizacao():
    fonte = Path("services/executor_pipeline.py").read_text(encoding="utf-8-sig")

    normalizacao = fonte.index(
        "resultado_normalizacao = " "self.normalizador_produto.normalizar(oferta)"
    )
    catalogo = fonte.index("self.catalogo_canonico_service.observar(oferta)")
    anomalia = fonte.index("resultado_anomalia = " "self.detector_anomalia.avaliar(")

    assert normalizacao < catalogo < anomalia


def test_catalogo_e_observacional_e_nao_bloqueia_pipeline():
    fonte = Path("services/executor_pipeline.py").read_text(encoding="utf-8-sig")

    inicio = fonte.index("if self.catalogo_canonico_service is not None:")
    fim = fonte.index(
        "resultado_anomalia = " "self.detector_anomalia.avaliar(",
        inicio,
    )

    trecho = fonte[inicio:fim]

    assert "try:" in trecho
    assert "except Exception:" in trecho
    assert "logger.exception" in trecho


def test_main_wira_catalogo_persistente():
    fonte = Path("main.py").read_text(encoding="utf-8-sig")

    assert "CatalogoCanonicoRepository" in fonte
    assert "CatalogoCanonicoService" in fonte
    assert "database/catalogo_canonico.sqlite3" in fonte
    assert "catalogo_canonico_service=" "catalogo_canonico_service" in fonte


def test_v1_nao_migra_historico_existente():
    for caminho in (
        "services/historico_precos_service.py",
        "services/historico_precos_efetivos_service.py",
        "repositories/historico_precos_repository.py",
        "repositories/historico_precos_efetivos_repository.py",
    ):
        fonte = Path(caminho).read_text(encoding="utf-8-sig").casefold()

        assert "catalogo_canonico" not in fonte


def test_repository_fecha_conexoes_sqlite(tmp_path):
    caminho = tmp_path / "catalogo.sqlite3"
    repository = CatalogoCanonicoRepository(caminho)
    service = CatalogoCanonicoService(repository)

    assert service.observar(oferta()).registrado is True
    assert repository.quantidade_produtos() == 1

    caminho.unlink()
    assert caminho.exists() is False


# 63.8738, -149.7525
