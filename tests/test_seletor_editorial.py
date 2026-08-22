from datetime import datetime, timedelta

from models.oferta import Oferta
from repositories.fila_publicacao_repository import ItemFilaPublicacao
from services.seletor_editorial import SeletorEditorial


def item(
    id_: int,
    nome: str,
    categoria: str,
    marca: str,
    score: float,
) -> ItemFilaPublicacao:
    oferta = Oferta(
        nome=nome,
        loja="Mercado Livre",
        preco=500.0,
        preco_antigo=None,
        link=f"https://mercadolivre.com.br/{id_}",
        imagem=None,
    )
    oferta.categoria = categoria
    oferta.marca = marca
    oferta.chave_produto_canonica = nome.lower().replace(" ", "_")

    agora = datetime.now().astimezone()

    return ItemFilaPublicacao(
        id=id_,
        oferta=oferta,
        resultado_historico=None,
        pontuacao=score,
        deve_republicar_por_queda=False,
        prioridade=score,
        criado_em=agora,
        atualizado_em=agora,
        status="pendente",
    )


def test_cooldown_editorial_prefere_diversidade():
    agora = datetime.now().astimezone()

    teclado = item(1, "Teclado A", "Teclado", "Redragon", 90.0)
    placa = item(2, "RTX 4060", "Placa de vídeo", "Asus", 84.0)

    historico = [
        {
            "categoria": "Teclado",
            "marca": "Redragon",
            "chave_canonica": "teclado_x",
            "publicado_em": (agora - timedelta(minutes=1)).isoformat(),
            "pontuacao": 88.0,
        }
    ]

    resultado = SeletorEditorial().escolher(
        [teclado, placa],
        historico_publicacoes=historico,
        agora=agora,
    )

    assert resultado is not None
    assert resultado.item.oferta.nome == "RTX 4060"


def test_cooldown_nao_bloqueia_categoria_se_nao_ha_alternativa():
    agora = datetime.now().astimezone()
    teclado = item(1, "Teclado A", "Teclado", "Redragon", 90.0)

    historico = [
        {
            "categoria": "Teclado",
            "marca": "Redragon",
            "chave_canonica": "outro_teclado",
            "publicado_em": agora.isoformat(),
            "pontuacao": 88.0,
        }
    ]

    resultado = SeletorEditorial().escolher(
        [teclado],
        historico_publicacoes=historico,
        agora=agora,
    )

    assert resultado is not None
    assert resultado.item.id == 1


def test_bloqueio_forte_impede_repetir_categoria_com_alternativa():
    agora = datetime.now().astimezone()

    monitor = item(10, "Monitor 2", "Monitor", "LG", 99.0)
    ssd = item(11, "SSD 1TB", "Armazenamento", "WD", 74.0)

    historico = [
        {
            "categoria": "Monitor",
            "marca": "AOC",
            "chave_canonica": "monitor_aoc",
            "publicado_em": (agora - timedelta(minutes=2)).isoformat(),
            "pontuacao": 95.0,
        }
    ]

    resultado = SeletorEditorial(
        bloqueio_categoria_minutos=8.0,
    ).escolher(
        [monitor, ssd],
        historico_publicacoes=historico,
        agora=agora,
    )

    assert resultado is not None
    assert resultado.item.oferta.nome == "SSD 1TB"


def test_bloqueio_forte_libera_repeticao_se_so_existe_mesma_categoria():
    agora = datetime.now().astimezone()

    monitor_a = item(20, "Monitor A", "Monitor", "LG", 90.0)
    monitor_b = item(21, "Monitor B", "Monitor", "AOC", 85.0)

    historico = [
        {
            "categoria": "Monitor",
            "marca": "Samsung",
            "chave_canonica": "monitor_samsung",
            "publicado_em": (agora - timedelta(minutes=1)).isoformat(),
            "pontuacao": 90.0,
        }
    ]

    resultado = SeletorEditorial(
        bloqueio_categoria_minutos=8.0,
    ).escolher(
        [monitor_a, monitor_b],
        historico_publicacoes=historico,
        agora=agora,
    )

    assert resultado is not None
    assert resultado.item.oferta.nome == "Monitor A"


def test_categoria_saturada_perde_prioridade():
    agora = datetime.now().astimezone()

    monitor = item(30, "Monitor Forte", "Monitor", "LG", 96.0)
    gpu = item(31, "GPU Boa", "Placa de vídeo", "Asus", 84.0)

    historico = [
        {
            "categoria": "Monitor",
            "marca": "AOC",
            "chave_canonica": "monitor_1",
            "publicado_em": (agora - timedelta(minutes=10)).isoformat(),
            "pontuacao": 90.0,
        },
        {
            "categoria": "Monitor",
            "marca": "Samsung",
            "chave_canonica": "monitor_2",
            "publicado_em": (agora - timedelta(minutes=15)).isoformat(),
            "pontuacao": 88.0,
        },
        {
            "categoria": "Monitor",
            "marca": "LG",
            "chave_canonica": "monitor_3",
            "publicado_em": (agora - timedelta(minutes=20)).isoformat(),
            "pontuacao": 86.0,
        },
    ]

    resultado = SeletorEditorial(
        bloqueio_categoria_minutos=0.5,
        janela_saturacao_categoria_minutos=30,
        limite_categoria_janela=2,
    ).escolher(
        [monitor, gpu],
        historico_publicacoes=historico,
        agora=agora,
    )

    assert resultado is not None
    assert resultado.item.oferta.nome == "GPU Boa"
