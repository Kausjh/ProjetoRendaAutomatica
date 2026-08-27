from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from models.oferta import Oferta
from repositories.radar_editorial_repository import RadarEditorialRepository
from services.historico_precos_service import ResultadoHistoricoPreco
from services.radar_editorial import RadarEditorial


class RngFake:
    def random(self) -> float:
        return 0.0

    def choice(self, itens):
        return itens[0]

    def randint(self, minimo: int, maximo: int) -> int:
        return minimo


def oferta(
    nome: str,
    categoria: str = "Processador",
    marca: str | None = "intel",
) -> Oferta:
    item = Oferta(
        nome=nome,
        loja="Mercado Livre",
        preco=500.0,
        preco_antigo=650.0,
        link="https://example.com/oferta",
        imagem=None,
    )
    item.categoria = categoria
    item.marca = marca
    return item


def historico(
    variacao: float = -20.0,
    *,
    menor_preco: bool = False,
) -> ResultadoHistoricoPreco:
    return ResultadoHistoricoPreco(
        primeiro_registro=False,
        preco_anterior=650.0,
        menor_preco_anterior=520.0,
        menor_preco_historico=menor_preco,
        variacao_percentual=variacao,
        preco_caiu=variacao < 0,
        preco_subiu=variacao > 0,
        novo_preco_registrado=True,
        quantidade_registros=5,
    )


def criar_editorial(tmp_path) -> RadarEditorial:
    repo = RadarEditorialRepository(tmp_path / "editorial.json")
    return RadarEditorial(
        repository=repo,
        rng=RngFake(),
    )


def test_kit_upgrade_legado_ganha_comentario_contextual(tmp_path):
    editorial = criar_editorial(tmp_path)
    agora = datetime(2026, 8, 26, 14, 0, tzinfo=UTC)

    resultado = editorial.avaliar_oferta(
        oferta=oferta("Kit Upgrade Intel Core i5-4570 16GB DDR3"),
        resultado_historico=None,
        pontuacao=62.0,
        deve_republicar_por_queda=False,
        agora=agora,
    )

    assert resultado is not None
    assert resultado.motivo == "contexto_upgrade_antigo"
    assert "upgrade" in resultado.texto.casefold()
    assert resultado.persona == "estagiario"


def test_republicacao_por_queda_explica_por_que_voltou(tmp_path):
    editorial = criar_editorial(tmp_path)
    agora = datetime(2026, 8, 26, 14, 0, tzinfo=UTC)

    resultado = editorial.avaliar_oferta(
        oferta=oferta("Ryzen 7 5700X"),
        resultado_historico=historico(-18.0),
        pontuacao=76.0,
        deve_republicar_por_queda=True,
        agora=agora,
    )

    assert resultado is not None
    assert resultado.motivo == "republicacao_por_queda"
    assert "18%" in resultado.texto


def test_cooldown_impede_comentarios_em_sequencia(tmp_path):
    editorial = criar_editorial(tmp_path)
    agora = datetime(2026, 8, 26, 14, 0, tzinfo=UTC)

    editorial.repository.registrar_intervencao(
        persona="estagiario",
        motivo="teste",
        texto="comentário anterior",
        momento=agora,
    )

    resultado = editorial.avaliar_oferta(
        oferta=oferta("Kit Upgrade Intel Core i5-4570"),
        resultado_historico=None,
        pontuacao=60.0,
        deve_republicar_por_queda=False,
        agora=agora + timedelta(minutes=5),
    )

    assert resultado is None


def test_persona_nao_repete_se_houver_alternativa(tmp_path):
    editorial = criar_editorial(tmp_path)
    agora = datetime(2026, 8, 26, 14, 0, tzinfo=UTC)

    editorial.repository.registrar_intervencao(
        persona="estagiario",
        motivo="teste",
        texto="comentário anterior",
        momento=agora - timedelta(minutes=20),
    )

    resultado = editorial.avaliar_oferta(
        oferta=oferta("Kit Upgrade Intel Core i5-4570"),
        resultado_historico=None,
        pontuacao=60.0,
        deve_republicar_por_queda=False,
        agora=agora,
    )

    assert resultado is not None
    assert resultado.persona != "estagiario"


def test_memoria_editorial_persiste(tmp_path):
    caminho = tmp_path / "editorial.json"
    repo = RadarEditorialRepository(caminho)
    agora = datetime(2026, 8, 26, 14, 0, tzinfo=UTC)

    repo.registrar_intervencao(
        persona="fiscal",
        motivo="teste",
        texto="texto persistido",
        momento=agora,
    )

    reaberto = RadarEditorialRepository(caminho)

    assert reaberto.comentarios_no_dia(agora.date()) == 1
    assert reaberto.ultima_persona() == "fiscal"
    assert reaberto.textos_recentes(1) == ["texto persistido"]


def test_planejamento_escolhe_quatro_dias_por_semana(tmp_path):
    editorial = criar_editorial(tmp_path)
    segunda = date(2026, 8, 24)

    planos = [editorial.planejar_interacao(segunda + timedelta(days=indice)) for indice in range(7)]

    ativos = [plano for plano in planos if plano is not None]

    assert len(ativos) == 4

    for plano in ativos:
        assert 8 * 60 + 10 <= plano.minuto_do_dia <= 10 * 60 + 20
        assert plano.tipo in {"enquete", "reacao"}


def test_interacao_diaria_so_pode_ser_registrada_uma_vez_logicamente(tmp_path):
    caminho = tmp_path / "editorial.json"
    repo = RadarEditorialRepository(caminho)
    agora = datetime(2026, 8, 26, 9, 0, tzinfo=UTC)

    assert repo.interacao_diaria_enviada(agora.date()) is False

    repo.registrar_interacao_diaria(
        data_referencia=agora.date(),
        tipo="enquete",
        momento=agora,
    )

    assert repo.interacao_diaria_enviada(agora.date()) is True


def test_interacoes_da_mesma_semana_nao_repetem_texto(tmp_path):
    editorial = criar_editorial(tmp_path)
    segunda = date(2026, 8, 24)

    planos = [editorial.planejar_interacao(segunda + timedelta(days=indice)) for indice in range(7)]
    textos = [plano.texto for plano in planos if plano is not None]

    assert len(textos) == 4
    assert len(set(textos)) == 4


def test_contexto_gpu_fraca_nao_depende_de_kit_upgrade(tmp_path):
    editorial = criar_editorial(tmp_path)
    agora = datetime(2026, 8, 26, 14, 0, tzinfo=UTC)

    resultado = editorial.avaliar_oferta(
        oferta=oferta(
            "PC Gamer Intel Core i5 GT 1030 16GB SSD",
            categoria="Computador",
            marca=None,
        ),
        resultado_historico=None,
        pontuacao=65.0,
        deve_republicar_por_queda=False,
        agora=agora,
    )

    assert resultado is not None
    assert resultado.motivo == "contexto_gpu_antiga_entrada"
    assert "GT 1030" in resultado.texto.upper()


def test_marketing_4k_com_gpu_fraca_tem_prioridade_editorial(tmp_path):
    editorial = criar_editorial(tmp_path)
    agora = datetime(2026, 8, 26, 14, 0, tzinfo=UTC)

    resultado = editorial.avaliar_oferta(
        oferta=oferta(
            "PC Gamer 4K Intel Core i5 GT 1030 16GB SSD",
            categoria="Computador",
            marca=None,
        ),
        resultado_historico=None,
        pontuacao=65.0,
        deve_republicar_por_queda=False,
        agora=agora,
    )

    assert resultado is not None
    assert resultado.motivo == "contexto_marketing_gpu_desproporcional"


def test_cpu_antiga_avulsa_pode_ser_detectada_sem_gerar_comentario(tmp_path):
    editorial = criar_editorial(tmp_path)
    agora = datetime(2026, 8, 26, 14, 0, tzinfo=UTC)

    resultado = editorial.avaliar_oferta(
        oferta=oferta(
            "Processador Intel Core i5-4570 3.2GHz",
            categoria="Processador",
        ),
        resultado_historico=None,
        pontuacao=65.0,
        deve_republicar_por_queda=False,
        agora=agora,
    )

    assert resultado is None


def test_oferta_comum_de_score_baixo_fica_quieta(tmp_path):
    editorial = criar_editorial(tmp_path)
    agora = datetime(2026, 8, 26, 14, 0, tzinfo=UTC)

    resultado = editorial.avaliar_oferta(
        oferta=oferta(
            "Mouse Gamer USB RGB",
            categoria="Periféricos",
            marca=None,
        ),
        resultado_historico=None,
        pontuacao=68.0,
        deve_republicar_por_queda=False,
        agora=agora,
    )

    assert resultado is None


def test_oferta_comum_so_entra_no_comentario_generico_acima_da_regua(tmp_path):
    editorial = criar_editorial(tmp_path)
    agora = datetime(2026, 8, 26, 14, 0, tzinfo=UTC)

    resultado = editorial.avaliar_oferta(
        oferta=oferta(
            "Mouse Gamer USB RGB",
            categoria="Periféricos",
            marca=None,
        ),
        resultado_historico=None,
        pontuacao=76.0,
        deve_republicar_por_queda=False,
        agora=agora,
    )

    assert resultado is not None
    assert resultado.motivo == "comentario_contextual"


def test_contexto_leve_de_score_baixo_fica_quieto(tmp_path):
    editorial = criar_editorial(tmp_path)
    agora = datetime(2026, 8, 26, 14, 0, tzinfo=UTC)

    resultado = editorial.avaliar_oferta(
        oferta=oferta(
            "Monitor Gamer 24 Full HD 75Hz",
            categoria="Monitor",
            marca=None,
        ),
        resultado_historico=None,
        pontuacao=66.0,
        deve_republicar_por_queda=False,
        agora=agora,
    )

    assert resultado is None


def test_contexto_leve_com_score_bom_pode_ser_comentado(tmp_path):
    editorial = criar_editorial(tmp_path)
    agora = datetime(2026, 8, 26, 14, 0, tzinfo=UTC)

    resultado = editorial.avaliar_oferta(
        oferta=oferta(
            "Monitor Gamer 24 Full HD 75Hz",
            categoria="Monitor",
            marca=None,
        ),
        resultado_historico=None,
        pontuacao=74.0,
        deve_republicar_por_queda=False,
        agora=agora,
    )

    assert resultado is not None
    assert resultado.motivo == "contexto_monitor_gamer_basico"


def test_incompatibilidade_tecnica_tem_prioridade_maxima(tmp_path):
    editorial = criar_editorial(tmp_path)
    agora = datetime(2026, 8, 26, 14, 0, tzinfo=UTC)

    resultado = editorial.avaliar_oferta(
        oferta=oferta(
            "Kit Upgrade Ryzen 5 5600G 16GB DDR3",
            categoria="Kit upgrade",
            marca=None,
        ),
        resultado_historico=historico(-20.0, menor_preco=True),
        pontuacao=90.0,
        deve_republicar_por_queda=True,
        agora=agora,
    )

    assert resultado is not None
    assert resultado.motivo == "contexto_incompatibilidade_memoria"
    assert "não" in resultado.texto.casefold() or "nao" in resultado.texto.casefold()


def test_cpu_basica_vendida_como_gamer_recebe_alerta_editorial(tmp_path):
    editorial = criar_editorial(tmp_path)
    agora = datetime(2026, 8, 26, 14, 0, tzinfo=UTC)

    resultado = editorial.avaliar_oferta(
        oferta=oferta(
            "PC Gamer Intel N100 16GB SSD 512GB",
            categoria="Computador",
            marca=None,
        ),
        resultado_historico=None,
        pontuacao=70.0,
        deve_republicar_por_queda=False,
        agora=agora,
    )

    assert resultado is not None
    assert resultado.motivo == "contexto_marketing_cpu_basica"
