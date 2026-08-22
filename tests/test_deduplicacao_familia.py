from datetime import datetime, timedelta
from pathlib import Path

from models.oferta import Oferta
from repositories.fila_publicacao_repository import FilaPublicacaoRepository
from services.identificador_familia_produto import IdentificadorFamiliaProduto
from services.seletor_editorial import SeletorEditorial


def oferta(nome: str, preco: float, marca: str = "Hyperx") -> Oferta:
    item = Oferta(
        nome=nome,
        loja="Mercado Livre",
        preco=preco,
        preco_antigo=None,
        link=f"https://mercadolivre.com.br/{abs(hash((nome, preco)))}",
        imagem=None,
    )
    item.categoria = "Áudio"
    item.marca = marca
    item.nota_final = 75
    return item


def test_cloud_ii_preto_e_vermelho_mesma_familia():
    identificador = IdentificadorFamiliaProduto()

    preto = oferta(
        "Headset Gamer Cloud Il Surround 7.1 USB Khx-hscp-rd " "Hyperx Preto",
        448,
    )
    vermelho = oferta(
        "Headset Gamer Cloud Il Surround 7.1 USB Khx-hscp-rd " "Hyperx C Cor Vermelho",
        426,
    )

    a = identificador.identificar(preto)
    b = identificador.identificar(vermelho)

    assert a.chave_familia == b.chave_familia
    assert identificador.mesma_familia(preto, vermelho)


def test_capacidade_diferente_nao_colide():
    identificador = IdentificadorFamiliaProduto()

    a = oferta("SSD Kingston NV2 NVMe 1TB Preto", 400, "Kingston")
    b = oferta("SSD Kingston NV2 NVMe 2TB Preto", 650, "Kingston")
    a.categoria = b.categoria = "Armazenamento"

    assert not identificador.mesma_familia(a, b)


def test_fila_mantem_so_o_cloud_ii_mais_barato(tmp_path: Path):
    repo = FilaPublicacaoRepository(str(tmp_path / "fila.sqlite3"))

    caro = oferta(
        "Headset Gamer Cloud Il Surround 7.1 USB Khx-hscp-rd " "Hyperx Preto",
        448,
    )
    barato = oferta(
        "Headset Gamer Cloud Il Surround 7.1 USB Khx-hscp-rd " "Hyperx C Cor Vermelho",
        426,
    )

    assert repo.adicionar_ou_atualizar(caro, None, 75, False, 80) == "adicionado"
    resultado = repo.adicionar_ou_atualizar(barato, None, 75, False, 79)

    assert resultado == "substituido_familia"

    pendentes = repo.listar_pendentes()
    assert len(pendentes) == 1
    assert pendentes[0].oferta.preco == 426


def test_cooldown_familia_bloqueia_repost_sem_queda():
    identificador = IdentificadorFamiliaProduto()
    item = oferta(
        "Headset Gamer Cloud Il Surround 7.1 USB Khx-hscp-rd " "Hyperx Preto",
        448,
    )
    identificador.identificar(item)

    from repositories.fila_publicacao_repository import ItemFilaPublicacao

    fila = ItemFilaPublicacao(
        id=1,
        oferta=item,
        resultado_historico=None,
        pontuacao=75,
        deve_republicar_por_queda=False,
        prioridade=80,
        criado_em=datetime.now().astimezone(),
        atualizado_em=datetime.now().astimezone(),
        status="pendente",
    )

    historico = [
        {
            "chave_familia": item.chave_familia_produto,
            "publicado_em": (datetime.now().astimezone() - timedelta(hours=2)).isoformat(),
            "preco": 448.0,
        }
    ]

    seletor = SeletorEditorial(cooldown_familia_minutos=720)

    assert seletor.escolher([fila], historico) is None


def test_queda_real_de_mais_de_5_porcento_fura_cooldown():
    identificador = IdentificadorFamiliaProduto()
    item = oferta(
        "Headset Gamer Cloud Il Surround 7.1 USB Khx-hscp-rd " "Hyperx Vermelho",
        420,
    )
    identificador.identificar(item)

    from repositories.fila_publicacao_repository import ItemFilaPublicacao

    fila = ItemFilaPublicacao(
        id=1,
        oferta=item,
        resultado_historico=None,
        pontuacao=75,
        deve_republicar_por_queda=True,
        prioridade=80,
        criado_em=datetime.now().astimezone(),
        atualizado_em=datetime.now().astimezone(),
        status="pendente",
    )

    historico = [
        {
            "chave_familia": item.chave_familia_produto,
            "publicado_em": (datetime.now().astimezone() - timedelta(hours=2)).isoformat(),
            "preco": 448.0,
        }
    ]

    seletor = SeletorEditorial(
        cooldown_familia_minutos=720,
        queda_minima_repost_familia_percentual=5,
    )

    assert seletor.escolher([fila], historico) is not None
