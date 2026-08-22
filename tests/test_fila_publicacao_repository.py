from models.oferta import Oferta
from repositories.fila_publicacao_repository import FilaPublicacaoRepository


def criar_oferta(link: str, nome: str = "RTX 4060") -> Oferta:
    oferta = Oferta(
        nome=nome,
        loja="Mercado Livre",
        preco=1999.0,
        preco_antigo=2299.0,
        link=link,
        imagem=None,
    )
    oferta.categoria = "Placa de vídeo"
    oferta.marca = "Asus"
    oferta.chave_produto_canonica = "rtx_4060"
    oferta.produto_canonico = "RTX 4060"
    oferta.confianca_normalizacao = 95.0
    oferta.nota_curadoria = 85.0
    return oferta


def test_fila_persiste_e_nao_duplica_link(tmp_path):
    caminho = tmp_path / "fila.sqlite3"
    repo = FilaPublicacaoRepository(str(caminho))
    oferta = criar_oferta("https://mercadolivre.com.br/a")

    assert (
        repo.adicionar_ou_atualizar(
            oferta=oferta,
            resultado_historico=None,
            pontuacao=80.0,
            deve_republicar_por_queda=False,
            prioridade=88.0,
        )
        == "adicionado"
    )

    resultado = repo.adicionar_ou_atualizar(
        oferta=oferta,
        resultado_historico=None,
        pontuacao=82.0,
        deve_republicar_por_queda=False,
        prioridade=90.0,
    )

    assert resultado == "atualizado"
    assert repo.quantidade_pendente() == 1
    assert repo.listar_pendentes()[0].pontuacao == 82.0


def test_fila_substitui_mesmo_produto_canonico_por_opcao_melhor(tmp_path):
    repo = FilaPublicacaoRepository(str(tmp_path / "fila.sqlite3"))

    antiga = criar_oferta("https://mercadolivre.com.br/a")
    nova = criar_oferta("https://mercadolivre.com.br/b")

    repo.adicionar_ou_atualizar(
        oferta=antiga,
        resultado_historico=None,
        pontuacao=80.0,
        deve_republicar_por_queda=False,
        prioridade=80.0,
    )

    resultado = repo.adicionar_ou_atualizar(
        oferta=nova,
        resultado_historico=None,
        pontuacao=90.0,
        deve_republicar_por_queda=False,
        prioridade=90.0,
    )

    assert resultado == "substituido_canonico"
    pendentes = repo.listar_pendentes()
    assert len(pendentes) == 1
    assert pendentes[0].oferta.link.endswith("/b")
