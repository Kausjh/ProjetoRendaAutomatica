from datetime import datetime, timedelta
from types import SimpleNamespace

from models.oferta import Oferta
from repositories.fila_publicacao_repository import (
    ItemFilaPublicacao,
)
from services.executor_pipeline import ExecutorPipeline
from services.seletor_editorial import SeletorEditorial


def criar_oferta(
    indice: int,
    loja: str,
    marketplace: str,
    score: float,
    categoria: str,
) -> tuple[Oferta, float, None, bool]:
    oferta = Oferta(
        nome=f"Produto {indice}",
        loja=loja,
        preco=100.0,
        preco_antigo=None,
        link=f"https://example.com/{indice}",
        imagem=None,
        marketplace=marketplace,
    )

    oferta.categoria = categoria
    oferta.marca = f"Marca {indice}"
    oferta.tipo_oportunidade = "normal"
    oferta.chave_produto_canonica = f"produto_{indice}"

    return (
        oferta,
        score,
        None,
        False,
    )


def criar_item_fila(
    indice: int,
    loja: str,
    marketplace: str,
    score: float,
    categoria: str,
) -> ItemFilaPublicacao:
    oferta = criar_oferta(
        indice=indice,
        loja=loja,
        marketplace=marketplace,
        score=score,
        categoria=categoria,
    )[0]

    agora = datetime.now().astimezone()

    return ItemFilaPublicacao(
        id=indice,
        oferta=oferta,
        resultado_historico=None,
        pontuacao=score,
        deve_republicar_por_queda=False,
        prioridade=score,
        criado_em=agora,
        atualizado_em=agora,
        status="pendente",
    )


def test_reserva_inclui_melhor_shopee_qualificada() -> None:
    ml = criar_oferta(
        1,
        "Mercado Livre",
        "mercado_livre",
        80.0,
        "Processador",
    )

    shopee = criar_oferta(
        2,
        "Shopee",
        "shopee",
        60.0,
        "Mouse",
    )

    resultado, reservas = ExecutorPipeline._garantir_diversidade_marketplace(
        selecionados=[ml],
        candidatos_disponiveis=[ml, shopee],
        pontuacao_minima=45.0,
    )

    marketplaces = {ExecutorPipeline._chave_marketplace(item[0]) for item in resultado}

    assert reservas == 1
    assert marketplaces == {
        "mercado_livre",
        "shopee",
    }


def test_reserva_inclui_aliexpress_em_cold_start_qualificado() -> None:
    ml = criar_oferta(
        10,
        "Mercado Livre",
        "mercado_livre",
        80.0,
        "Processador",
    )

    aliexpress_base = criar_oferta(
        11,
        "AliExpress",
        "aliexpress",
        30.0,
        "Armazenamento",
    )

    aliexpress_base[0].nota_tecnica = 30.0

    aliexpress = (
        aliexpress_base[0],
        aliexpress_base[1],
        SimpleNamespace(
            primeiro_registro=True,
        ),
        aliexpress_base[3],
    )

    resultado, reservas = ExecutorPipeline._garantir_diversidade_marketplace(
        selecionados=[ml],
        candidatos_disponiveis=[
            ml,
            aliexpress,
        ],
        pontuacao_minima=45.0,
        pontuacao_minima_cold_start=72.0,
    )

    marketplaces = {ExecutorPipeline._chave_marketplace(item[0]) for item in resultado}

    assert reservas == 1
    assert "aliexpress" in marketplaces


def test_reserva_rejeita_cold_start_tecnico_fraco() -> None:
    ml = criar_oferta(
        20,
        "Mercado Livre",
        "mercado_livre",
        80.0,
        "Processador",
    )

    aliexpress_base = criar_oferta(
        21,
        "AliExpress",
        "aliexpress",
        28.0,
        "Armazenamento",
    )

    aliexpress_base[0].nota_tecnica = 28.0

    aliexpress = (
        aliexpress_base[0],
        aliexpress_base[1],
        SimpleNamespace(
            primeiro_registro=True,
        ),
        aliexpress_base[3],
    )

    resultado, reservas = ExecutorPipeline._garantir_diversidade_marketplace(
        selecionados=[ml],
        candidatos_disponiveis=[
            ml,
            aliexpress,
        ],
        pontuacao_minima=45.0,
        pontuacao_minima_cold_start=72.0,
    )

    marketplaces = {ExecutorPipeline._chave_marketplace(item[0]) for item in resultado}

    assert reservas == 0
    assert "aliexpress" not in marketplaces


def test_reserva_nao_trata_historico_existente_como_cold_start() -> None:
    ml = criar_oferta(
        30,
        "Mercado Livre",
        "mercado_livre",
        80.0,
        "Processador",
    )

    aliexpress_base = criar_oferta(
        31,
        "AliExpress",
        "aliexpress",
        40.0,
        "Armazenamento",
    )

    aliexpress_base[0].nota_tecnica = 40.0

    aliexpress = (
        aliexpress_base[0],
        aliexpress_base[1],
        SimpleNamespace(
            primeiro_registro=False,
        ),
        aliexpress_base[3],
    )

    resultado, reservas = ExecutorPipeline._garantir_diversidade_marketplace(
        selecionados=[ml],
        candidatos_disponiveis=[
            ml,
            aliexpress,
        ],
        pontuacao_minima=45.0,
        pontuacao_minima_cold_start=72.0,
    )

    marketplaces = {ExecutorPipeline._chave_marketplace(item[0]) for item in resultado}

    assert reservas == 0
    assert "aliexpress" not in marketplaces


def test_entrada_da_fila_preserva_os_dois_marketplaces() -> None:
    candidatos = [
        criar_oferta(
            1,
            "Mercado Livre",
            "mercado_livre",
            95.0,
            "Monitor",
        ),
        criar_oferta(
            2,
            "Mercado Livre",
            "mercado_livre",
            94.0,
            "Processador",
        ),
        criar_oferta(
            3,
            "Mercado Livre",
            "mercado_livre",
            93.0,
            "Armazenamento",
        ),
        criar_oferta(
            4,
            "Shopee",
            "shopee",
            60.0,
            "Mouse",
        ),
    ]

    selecionados = ExecutorPipeline._selecionar_candidatos_diversos(
        candidatos=candidatos,
        limite_total=3,
        limite_por_categoria=2,
    )

    marketplaces = {ExecutorPipeline._chave_marketplace(item[0]) for item in selecionados}

    assert "mercado_livre" in marketplaces
    assert "shopee" in marketplaces


def test_publicador_prefere_shopee_apos_mercado_livre() -> None:
    agora = datetime.now().astimezone()

    ml = criar_item_fila(
        1,
        "Mercado Livre",
        "mercado_livre",
        95.0,
        "Processador",
    )

    shopee = criar_item_fila(
        2,
        "Shopee",
        "shopee",
        65.0,
        "Mouse",
    )

    historico = [
        {
            "marketplace": "mercado_livre",
            "loja": "Mercado Livre",
            "categoria": "Monitor",
            "marca": "Outra Marca",
            "chave_canonica": "produto_antigo",
            "chave_familia": "",
            "publicado_em": (agora - timedelta(minutes=1)).isoformat(),
            "pontuacao": 80.0,
        }
    ]

    resultado = SeletorEditorial().escolher(
        [ml, shopee],
        historico_publicacoes=historico,
        agora=agora,
    )

    assert resultado is not None
    assert resultado.item.oferta.loja == "Shopee"


def test_publicador_nao_para_se_so_houver_mercado_livre() -> None:
    agora = datetime.now().astimezone()

    ml = criar_item_fila(
        1,
        "Mercado Livre",
        "mercado_livre",
        90.0,
        "Processador",
    )

    historico = [
        {
            "marketplace": "mercado_livre",
            "loja": "Mercado Livre",
            "categoria": "Monitor",
            "marca": "Outra Marca",
            "chave_canonica": "produto_antigo",
            "chave_familia": "",
            "publicado_em": (agora - timedelta(minutes=1)).isoformat(),
            "pontuacao": 80.0,
        }
    ]

    resultado = SeletorEditorial().escolher(
        [ml],
        historico_publicacoes=historico,
        agora=agora,
    )

    assert resultado is not None
    assert resultado.item.oferta.loja == "Mercado Livre"


def test_oportunidade_urgente_pode_furar_alternancia() -> None:
    agora = datetime.now().astimezone()

    ml = criar_item_fila(
        1,
        "Mercado Livre",
        "mercado_livre",
        95.0,
        "Processador",
    )
    ml.oferta.tipo_oportunidade = "anomalia_forte"

    shopee = criar_item_fila(
        2,
        "Shopee",
        "shopee",
        65.0,
        "Mouse",
    )

    historico = [
        {
            "marketplace": "mercado_livre",
            "loja": "Mercado Livre",
            "categoria": "Monitor",
            "marca": "Outra Marca",
            "chave_canonica": "produto_antigo",
            "chave_familia": "",
            "publicado_em": (agora - timedelta(minutes=1)).isoformat(),
            "pontuacao": 80.0,
        }
    ]

    resultado = SeletorEditorial().escolher(
        [ml, shopee],
        historico_publicacoes=historico,
        agora=agora,
    )

    assert resultado is not None
    assert resultado.item.oferta.loja == "Mercado Livre"
