from datetime import datetime, timedelta

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


def test_fila_segura_agenda_e_libera_item(tmp_path):
    repo = FilaPublicacaoRepository(str(tmp_path / "fila.sqlite3"))
    oferta = criar_oferta("https://mercadolivre.com.br/agendada")

    repo.adicionar_ou_atualizar(
        oferta=oferta,
        resultado_historico=None,
        pontuacao=88.0,
        deve_republicar_por_queda=False,
        prioridade=88.0,
    )

    item_id = repo.listar_pendentes(limite=1)[0].id

    assert repo.segurar_item(item_id, 15) is True

    segurado = repo.obter_pendente_por_id(item_id)

    assert segurado is not None
    assert segurado.segurado_ate is not None
    assert segurado.agendado_para is None

    para = (datetime.now().astimezone() + timedelta(minutes=30)).replace(microsecond=0)

    assert repo.agendar_item(item_id, para) is True

    agendado = repo.obter_pendente_por_id(item_id)

    assert agendado is not None
    assert agendado.segurado_ate is None
    assert agendado.agendado_para == para

    assert repo.liberar_item(item_id) is True

    liberado = repo.obter_pendente_por_id(item_id)

    assert liberado is not None
    assert liberado.segurado_ate is None
    assert liberado.agendado_para is None


def test_agendado_so_fica_liberado_depois_do_horario(tmp_path):
    repo = FilaPublicacaoRepository(str(tmp_path / "fila.sqlite3"))
    oferta = criar_oferta("https://mercadolivre.com.br/depois")

    repo.adicionar_ou_atualizar(
        oferta=oferta,
        resultado_historico=None,
        pontuacao=91.0,
        deve_republicar_por_queda=False,
        prioridade=91.0,
    )

    item_id = repo.listar_pendentes(limite=1)[0].id
    agora = datetime.now().astimezone().replace(microsecond=0)
    para = agora + timedelta(minutes=10)

    assert repo.agendar_item(item_id, para) is True

    assert (
        repo.obter_agendado_liberado(
            agora=para - timedelta(seconds=1),
        )
        is None
    )

    liberado = repo.obter_agendado_liberado(
        agora=para + timedelta(seconds=1),
    )

    assert liberado is not None
    assert liberado.id == item_id


def test_aprovacao_manual_persiste_na_fila(tmp_path):
    repo = FilaPublicacaoRepository(str(tmp_path / "fila.sqlite3"))
    oferta = criar_oferta("https://mercadolivre.com.br/aprovacao")

    repo.adicionar_ou_atualizar(
        oferta=oferta,
        resultado_historico=None,
        pontuacao=75.0,
        deve_republicar_por_queda=False,
        prioridade=75.0,
    )

    item_id = repo.listar_pendentes(limite=1)[0].id

    assert repo.aprovar_item(item_id) is True

    aprovado = repo.obter_pendente_por_id(item_id)

    assert aprovado is not None
    assert aprovado.aprovado_manualmente is True

    assert repo.revisar_item(item_id) is True

    revisado = repo.obter_pendente_por_id(item_id)

    assert revisado is not None
    assert revisado.aprovado_manualmente is False


def test_fila_preserva_precos_condicionais_aliexpress(
    tmp_path,
):
    repo = FilaPublicacaoRepository(str(tmp_path / "fila.sqlite3"))

    oferta = Oferta(
        nome="Produto AliExpress",
        loja="AliExpress",
        preco=40.04,
        preco_antigo=None,
        link=("https://pt.aliexpress.com/" "item/1005000000000001.html"),
        imagem=None,
        moeda="R$",
        marketplace="aliexpress",
        preco_novo_usuario=25.04,
        moeda_novo_usuario="BRL",
        preco_origem=8.96,
        moeda_origem="CNY",
    )

    resultado = repo.adicionar_ou_atualizar(
        oferta=oferta,
        resultado_historico=None,
        pontuacao=70.0,
        deve_republicar_por_queda=False,
        prioridade=70.0,
    )

    assert resultado == "adicionado"

    pendentes = repo.listar_pendentes()

    assert len(pendentes) == 1

    restaurada = pendentes[0].oferta

    assert restaurada.preco == 40.04

    assert restaurada.preco_novo_usuario == 25.04

    assert restaurada.moeda_novo_usuario == "BRL"

    assert restaurada.preco_origem == 8.96

    assert restaurada.moeda_origem == "CNY"
