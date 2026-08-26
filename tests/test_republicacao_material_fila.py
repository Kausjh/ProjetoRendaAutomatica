from datetime import datetime, timedelta
from types import SimpleNamespace

from models.oferta import Oferta
from repositories.fila_publicacao_repository import FilaPublicacaoRepository
from services.executor_pipeline import ExecutorPipeline


def criar_oferta(link: str, preco: float) -> Oferta:
    oferta = Oferta(
        nome="Monitor Gamer Teste 300Hz",
        loja="Mercado Livre",
        preco=preco,
        preco_antigo=None,
        link=link,
        imagem=None,
    )
    oferta.categoria = "Monitor"
    oferta.marca = "teste"
    oferta.chave_produto_canonica = "monitor_teste_300hz"
    oferta.produto_canonico = "Monitor Teste 300Hz"
    oferta.confianca_normalizacao = 95.0
    oferta.chave_familia_produto = "monitor_teste_300hz"
    oferta.familia_produto = "monitor teste 300hz"
    oferta.confianca_familia = 95.0
    oferta.nota_curadoria = 85.0
    return oferta


def publicar(repo: FilaPublicacaoRepository) -> int:
    item = repo.listar_pendentes()[0]
    repo.marcar_publicado(item.id)
    return item.id


def test_link_publicado_pode_ser_reativado_por_queda_e_preserva_historico(tmp_path):
    repo = FilaPublicacaoRepository(str(tmp_path / "fila.sqlite3"))
    link = "https://mercadolivre.com.br/oferta-teste"

    primeira = criar_oferta(link, 1555.0)
    assert (
        repo.adicionar_ou_atualizar(
            oferta=primeira,
            resultado_historico=None,
            pontuacao=69.0,
            deve_republicar_por_queda=False,
            prioridade=75.0,
        )
        == "adicionado"
    )
    publicar(repo)

    segunda = criar_oferta(link, 1299.0)
    resultado = repo.adicionar_ou_atualizar(
        oferta=segunda,
        resultado_historico=None,
        pontuacao=69.78,
        deve_republicar_por_queda=True,
        prioridade=85.0,
        permitir_republicacao=True,
    )

    assert resultado == "reativado_por_queda"
    assert repo.quantidade_pendente() == 1

    publicar(repo)
    historico = repo.historico_publicacoes_recentes(
        minutos=60.0,
        limite=10,
    )

    assert len(historico) == 2
    assert [item["preco"] for item in historico] == [1299.0, 1555.0]


def test_link_publicado_continua_bloqueado_sem_autorizacao_de_republicacao(tmp_path):
    repo = FilaPublicacaoRepository(str(tmp_path / "fila.sqlite3"))
    link = "https://mercadolivre.com.br/oferta-sem-mudanca"
    oferta = criar_oferta(link, 999.0)

    repo.adicionar_ou_atualizar(
        oferta=oferta,
        resultado_historico=None,
        pontuacao=70.0,
        deve_republicar_por_queda=False,
        prioridade=75.0,
    )
    publicar(repo)

    resultado = repo.adicionar_ou_atualizar(
        oferta=oferta,
        resultado_historico=None,
        pontuacao=70.0,
        deve_republicar_por_queda=False,
        prioridade=75.0,
    )

    assert resultado == "ja_publicado_pela_fila"
    assert repo.quantidade_pendente() == 0


def test_queda_material_so_comeca_no_limite_configurado():
    abaixo = SimpleNamespace(preco_caiu=True, variacao_percentual=-4.99)
    limite = SimpleNamespace(preco_caiu=True, variacao_percentual=-5.0)

    assert ExecutorPipeline._obter_queda_percentual(abaixo) == 4.99
    assert ExecutorPipeline._obter_queda_percentual(limite) == 5.0


def test_republicacao_por_tempo_respeita_cooldown():
    class FilaFake:
        def __init__(self, instante):
            self.instante = instante

        def obter_ultima_publicacao_link(self, link):
            return self.instante

    agora = datetime.now().astimezone()
    executor = object.__new__(ExecutorPipeline)
    executor.cooldown_republicacao_sem_queda_minutos = 720.0

    executor.fila_publicacao_repository = FilaFake(agora - timedelta(minutes=719))
    assert executor._pode_republicar_por_tempo("https://example.com/a") is False

    executor.fila_publicacao_repository = FilaFake(agora - timedelta(minutes=721))
    assert executor._pode_republicar_por_tempo("https://example.com/a") is True
