import inspect
import json
import sqlite3

from models.oferta import Oferta
from repositories.fila_publicacao_repository import (
    FilaPublicacaoRepository,
)


def criar_oferta(
    indice: int,
    loja: str,
    marketplace: str,
    chave_canonica: str,
    chave_familia: str,
    preco: float,
) -> Oferta:
    oferta = Oferta(
        nome=f"Produto {indice}",
        loja=loja,
        preco=preco,
        preco_antigo=None,
        link=f"https://example.com/{marketplace}/{indice}",
        imagem=None,
        marketplace=marketplace,
    )

    oferta.categoria = "Mouse"
    oferta.marca = "Marca Teste"

    oferta.chave_produto_canonica = chave_canonica
    oferta.confianca_normalizacao = 95.0

    oferta.chave_familia_produto = chave_familia
    oferta.familia_produto = chave_familia
    oferta.confianca_familia = 95.0

    oferta.tipo_oportunidade = "normal"

    return oferta


def adicionar(
    repository: FilaPublicacaoRepository,
    oferta: Oferta,
    prioridade: float,
) -> str:
    kwargs = {
        "oferta": oferta,
        "resultado_historico": None,
        "pontuacao": prioridade,
        "deve_republicar_por_queda": False,
        "prioridade": prioridade,
    }

    parametros = inspect.signature(repository.adicionar_ou_atualizar).parameters

    if "permitir_republicacao" in parametros:
        kwargs["permitir_republicacao"] = False

    return repository.adicionar_ou_atualizar(**kwargs)


def lojas_no_banco(caminho) -> list[str]:
    conexao = sqlite3.connect(caminho)

    linhas = conexao.execute("""
        SELECT oferta_json
        FROM fila_publicacao
        WHERE status = 'pendente'
        ORDER BY id
        """).fetchall()

    conexao.close()

    return [json.loads(linha[0])["loja"] for linha in linhas]


def test_mesmo_produto_pode_existir_em_marketplaces_diferentes(
    tmp_path,
) -> None:
    caminho = tmp_path / "fila.sqlite3"

    repository = FilaPublicacaoRepository(str(caminho))

    mercado_livre = criar_oferta(
        indice=1,
        loja="Mercado Livre",
        marketplace="mercado_livre",
        chave_canonica="mouse-logitech-g305",
        chave_familia="mouse-logitech-g305",
        preco=200.0,
    )

    shopee = criar_oferta(
        indice=2,
        loja="Shopee",
        marketplace="shopee",
        chave_canonica="mouse-logitech-g305",
        chave_familia="mouse-logitech-g305",
        preco=180.0,
    )

    assert (
        adicionar(
            repository,
            mercado_livre,
            90.0,
        )
        == "adicionado"
    )

    assert (
        adicionar(
            repository,
            shopee,
            60.0,
        )
        == "adicionado"
    )

    assert lojas_no_banco(caminho) == [
        "Mercado Livre",
        "Shopee",
    ]


def test_mesma_familia_em_marketplaces_diferentes_nao_colide(
    tmp_path,
) -> None:
    caminho = tmp_path / "fila.sqlite3"

    repository = FilaPublicacaoRepository(str(caminho))

    mercado_livre = criar_oferta(
        indice=1,
        loja="Mercado Livre",
        marketplace="mercado_livre",
        chave_canonica="ssd-ml",
        chave_familia="ssd-nvme-1tb",
        preco=300.0,
    )

    shopee = criar_oferta(
        indice=2,
        loja="Shopee",
        marketplace="shopee",
        chave_canonica="ssd-shopee",
        chave_familia="ssd-nvme-1tb",
        preco=350.0,
    )

    assert (
        adicionar(
            repository,
            mercado_livre,
            90.0,
        )
        == "adicionado"
    )

    assert (
        adicionar(
            repository,
            shopee,
            60.0,
        )
        == "adicionado"
    )

    assert lojas_no_banco(caminho) == [
        "Mercado Livre",
        "Shopee",
    ]
