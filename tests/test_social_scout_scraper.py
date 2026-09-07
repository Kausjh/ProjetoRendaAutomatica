# 63.8738, -149.7525

from models.mensagem_social_scout import (
    MensagemSocialScout,
)
from models.oferta import Oferta
from models.resultado_construcao_oferta_social_scout import (
    ResultadoConstrucaoOfertaSocialScout,
)
from models.resultado_deteccao_social_scout import (
    ResultadoDeteccaoSocialScout,
)
from models.resultado_resolucao_social_scout import (
    ResultadoResolucaoSocialScout,
)
from models.resultado_validacao_preco_social_scout import (
    ResultadoValidacaoPrecoSocialScout,
)
from scrapers.social_scout_scraper import (
    SocialScoutScraper,
)


def mensagem(
    message_id: int,
    texto: str = "Mouse Gamer Teste",
    editado_em: str | None = None,
):
    return MensagemSocialScout(
        fonte="telegram",
        chat_id="-100123",
        message_id=message_id,
        chat_titulo="Grupo Teste",
        texto=texto,
        links=(f"https://meli.la/teste{message_id}",),
        editado_em=editado_em,
    )


class RepositoryFake:
    def __init__(
        self,
        mensagens,
    ):
        self.mensagens = list(mensagens)

    def listar(self):
        return list(self.mensagens)


class ProcessamentosFake:
    def __init__(
        self,
    ):
        self.estados = {}

    def _chave(
        self,
        msg,
        versao,
    ):
        return (
            msg.fonte,
            msg.chat_id,
            msg.message_id,
            str(versao),
        )

    def esta_processada(
        self,
        msg,
        versao_processador,
        fingerprint,
    ):
        estado = self.estados.get(
            self._chave(
                msg,
                versao_processador,
            )
        )

        return estado is not None and estado["fingerprint"] == fingerprint

    def salvar(
        self,
        mensagem,
        versao_processador,
        fingerprint,
        status,
        motivo="",
    ):
        self.estados[
            self._chave(
                mensagem,
                versao_processador,
            )
        ] = {
            "fingerprint": fingerprint,
            "status": status,
            "motivo": motivo,
        }

    def quantidade(
        self,
    ):
        return len(self.estados)


class DetectorFake:
    def __init__(
        self,
        *,
        classificacao="oferta_produto",
        marketplace="mercado_livre",
    ):
        self.classificacao = classificacao
        self.marketplace = marketplace
        self.ids_processados = []

    def detectar(
        self,
        msg,
    ):
        self.ids_processados.append(msg.message_id)

        return ResultadoDeteccaoSocialScout(
            classificacao=self.classificacao,
            utilizavel=True,
            titulo=msg.texto,
            marketplace=self.marketplace,
            preco_original=200.00,
            preco_oferta=100.00,
            links=msg.links,
            motivo="teste",
        )


class ResolvedorFake:
    def __init__(
        self,
        *,
        status="resolvido",
        id_produto=None,
    ):
        self.status = status
        self.id_produto = id_produto
        self.chamadas = 0

    def resolver(
        self,
        msg,
        deteccao,
    ):
        self.chamadas += 1

        identificador = self.id_produto or f"MLB{msg.message_id:08d}"

        return ResultadoResolucaoSocialScout(
            fonte="telegram",
            id_externo=(f"{msg.chat_id}:{msg.message_id}"),
            status=self.status,
            marketplace="mercado_livre",
            tipo_destino="produto",
            url_original=msg.links[0],
            url_destino=("https://www.mercadolivre.com.br/" f"produto/p/{identificador}"),
            id_produto=identificador,
            motivo="teste",
        )


class ResolvedorSequencialFake:
    def __init__(
        self,
        statuses,
    ):
        self.statuses = list(statuses)
        self.chamadas = 0

    def resolver(
        self,
        msg,
        deteccao,
    ):
        indice = min(
            self.chamadas,
            len(self.statuses) - 1,
        )

        status = self.statuses[indice]

        self.chamadas += 1

        identificador = f"MLB{msg.message_id:08d}"

        return ResultadoResolucaoSocialScout(
            fonte="telegram",
            id_externo=(f"{msg.chat_id}:{msg.message_id}"),
            status=status,
            marketplace="mercado_livre",
            tipo_destino="produto",
            url_original=msg.links[0],
            url_destino=("https://www.mercadolivre.com.br/" f"produto/p/{identificador}"),
            id_produto=identificador,
            motivo=("falha_temporaria" if status == "erro" else "teste"),
        )


class ValidadorFake:
    def __init__(
        self,
        *,
        status="validado",
    ):
        self.status = status
        self.chamadas = 0

    def validar(
        self,
        deteccao,
        resolucao,
    ):
        self.chamadas += 1

        return ResultadoValidacaoPrecoSocialScout(
            status=self.status,
            marketplace="mercado_livre",
            url=resolucao.url_destino,
            titulo_oficial=deteccao.titulo,
            preco_oficial=100.00,
            preco_original_oficial=200.00,
            tipo_preco_oficial="pix",
            disponivel=True,
            preco_original_grupo=200.00,
            preco_oferta_grupo=100.00,
            preco_base_confere=True,
            preco_original_confere=True,
            cupom_validado=False,
            motivo="teste",
        )


class ConstrutorFake:
    def __init__(
        self,
        *,
        status="criada",
    ):
        self.status = status

    def construir(
        self,
        deteccao,
        resolucao,
        validacao,
    ):
        if self.status != "criada":
            return ResultadoConstrucaoOfertaSocialScout(
                status="rejeitada",
                motivo="teste",
            )

        oferta = Oferta(
            nome=deteccao.titulo,
            loja="Mercado Livre",
            preco=validacao.preco_oficial,
            preco_antigo=(validacao.preco_original_oficial),
            link=resolucao.url_destino,
            imagem=None,
            marketplace="mercado_livre",
            id_produto=resolucao.id_produto,
        )

        return ResultadoConstrucaoOfertaSocialScout(
            status="criada",
            oferta=oferta,
            motivo="teste",
        )


def criar_scraper(
    mensagens,
    *,
    detector=None,
    resolvedor=None,
    validador=None,
    construtor=None,
    processamentos=None,
    max_mensagens=30,
):
    return SocialScoutScraper(
        repository=RepositoryFake(mensagens),
        processamentos_repository=(processamentos or ProcessamentosFake()),
        detector=(detector or DetectorFake()),
        resolvedor=(resolvedor or ResolvedorFake()),
        validador_preco=(validador or ValidadorFake()),
        construtor=(construtor or ConstrutorFake()),
        max_mensagens_por_execucao=(max_mensagens),
    )


def test_processa_mensagens_mais_recentes_primeiro():
    detector = DetectorFake()

    scraper = criar_scraper(
        [
            mensagem(1),
            mensagem(2),
            mensagem(3),
        ],
        detector=detector,
    )

    ofertas = scraper.buscar_ofertas(limite=2)

    assert len(ofertas) == 2

    assert detector.ids_processados == [
        3,
        2,
    ]


def test_limite_zero_nao_processa_mensagens():
    detector = DetectorFake()

    scraper = criar_scraper(
        [mensagem(1)],
        detector=detector,
    )

    assert scraper.buscar_ofertas(limite=0) == []

    assert detector.ids_processados == []


def test_ignora_mensagem_que_nao_e_oferta():
    scraper = criar_scraper(
        [mensagem(1)],
        detector=DetectorFake(classificacao="ignorar"),
    )

    assert scraper.buscar_ofertas() == []


def test_ignora_marketplace_ainda_nao_suportado():
    scraper = criar_scraper(
        [mensagem(1)],
        detector=DetectorFake(marketplace="kabum"),
    )

    assert scraper.buscar_ofertas() == []


def test_ignora_resolucao_nao_resolvida():
    scraper = criar_scraper(
        [mensagem(1)],
        resolvedor=ResolvedorFake(status="nao_suportado"),
    )

    assert scraper.buscar_ofertas() == []


def test_ignora_preco_nao_validado():
    scraper = criar_scraper(
        [mensagem(1)],
        validador=ValidadorFake(status="divergente"),
    )

    assert scraper.buscar_ofertas() == []


def test_ignora_construcao_rejeitada():
    scraper = criar_scraper(
        [mensagem(1)],
        construtor=ConstrutorFake(status="rejeitada"),
    )

    assert scraper.buscar_ofertas() == []


def test_remove_produto_duplicado_na_mesma_execucao():
    scraper = criar_scraper(
        [
            mensagem(1),
            mensagem(2),
        ],
        resolvedor=ResolvedorFake(id_produto="MLB99999999"),
    )

    ofertas = scraper.buscar_ofertas(limite=5)

    assert len(ofertas) == 1


def test_respeita_maximo_de_mensagens_por_execucao():
    detector = DetectorFake()

    scraper = criar_scraper(
        [
            mensagem(1),
            mensagem(2),
            mensagem(3),
            mensagem(4),
        ],
        detector=detector,
        max_mensagens=2,
    )

    ofertas = scraper.buscar_ofertas(limite=10)

    assert len(ofertas) == 2

    assert detector.ids_processados == [
        4,
        3,
    ]


def test_sem_ack_reemite_mesma_mensagem():
    processamentos = ProcessamentosFake()
    detector = DetectorFake()
    resolvedor = ResolvedorFake()

    scraper = criar_scraper(
        [mensagem(1)],
        processamentos=processamentos,
        detector=detector,
        resolvedor=resolvedor,
    )

    primeira = scraper.buscar_ofertas()
    segunda = scraper.buscar_ofertas()

    assert len(primeira) == 1
    assert len(segunda) == 1

    assert detector.ids_processados == [
        1,
        1,
    ]

    assert resolvedor.chamadas == 2

    assert processamentos.quantidade() == 0


def test_ack_terminal_impede_reprocessamento():
    processamentos = ProcessamentosFake()
    detector = DetectorFake()

    scraper = criar_scraper(
        [mensagem(1)],
        processamentos=processamentos,
        detector=detector,
    )

    ofertas = scraper.buscar_ofertas()

    assert len(ofertas) == 1

    assert scraper.confirmar_handoff(
        ofertas[0],
        status="pipeline_processada",
        motivo="teste",
    )

    assert scraper.buscar_ofertas() == []

    assert detector.ids_processados == [1]

    estado = next(iter(processamentos.estados.values()))

    assert estado["status"] == "pipeline_processada"


def test_reemissao_substitui_handoff_antigo():
    processamentos = ProcessamentosFake()

    scraper = criar_scraper(
        [mensagem(1)],
        processamentos=processamentos,
    )

    primeira = scraper.buscar_ofertas()
    segunda = scraper.buscar_ofertas()

    assert len(primeira) == 1
    assert len(segunda) == 1

    assert not scraper.confirmar_handoff(
        primeira[0],
        status="pipeline_processada",
        motivo="handoff_antigo",
    )

    assert scraper.confirmar_handoff(
        segunda[0],
        status="pipeline_processada",
        motivo="handoff_atual",
    )

    estado = next(iter(processamentos.estados.values()))

    assert estado["motivo"] == "handoff_atual"


def test_mensagem_editada_e_reprocessada():
    processamentos = ProcessamentosFake()
    detector = DetectorFake()

    scraper = criar_scraper(
        [mensagem(1)],
        processamentos=processamentos,
        detector=detector,
    )

    primeiro = scraper.buscar_ofertas()

    assert len(primeiro) == 1

    assert scraper.confirmar_handoff(
        primeiro[0],
        status="pipeline_processada",
        motivo="teste",
    )

    scraper.repository.mensagens = [
        mensagem(
            1,
            texto="Teclado Gamer Teste",
            editado_em="2026-09-06T17:00:00",
        )
    ]

    segundo = scraper.buscar_ofertas()

    assert len(segundo) == 1

    assert detector.ids_processados == [
        1,
        1,
    ]


def test_erro_transitorio_nao_bloqueia_tentativa_futura():
    processamentos = ProcessamentosFake()

    resolvedor = ResolvedorSequencialFake(
        [
            "erro",
            "resolvido",
        ]
    )

    scraper = criar_scraper(
        [mensagem(1)],
        processamentos=processamentos,
        resolvedor=resolvedor,
    )

    primeiro = scraper.buscar_ofertas()

    assert primeiro == []
    assert processamentos.quantidade() == 0

    segundo = scraper.buscar_ofertas()

    assert len(segundo) == 1
    assert resolvedor.chamadas == 2
    assert processamentos.quantidade() == 0


def test_modo_sombra_classifica_nicho_mas_nao_emite():
    processamentos = ProcessamentosFake()

    scraper = SocialScoutScraper(
        repository=RepositoryFake(
            [
                mensagem(
                    1,
                    texto="Mouse Gamer RGB Modelo Teste",
                )
            ]
        ),
        processamentos_repository=processamentos,
        detector=DetectorFake(),
        resolvedor=ResolvedorFake(),
        validador_preco=ValidadorFake(),
        construtor=ConstrutorFake(),
        max_mensagens_por_execucao=5,
        modo_sombra=True,
    )

    ofertas = scraper.buscar_ofertas(limite=5)

    assert ofertas == []

    assert processamentos.quantidade() == 1

    estado = next(iter(processamentos.estados.values()))

    assert estado["status"] == "sombra_nicho"


def test_modo_sombra_classifica_fora_do_nicho_sem_emitir():
    processamentos = ProcessamentosFake()

    scraper = SocialScoutScraper(
        repository=RepositoryFake(
            [
                mensagem(
                    1,
                    texto="Camiseta Gamer Modelo Teste",
                )
            ]
        ),
        processamentos_repository=processamentos,
        detector=DetectorFake(),
        resolvedor=ResolvedorFake(),
        validador_preco=ValidadorFake(),
        construtor=ConstrutorFake(),
        max_mensagens_por_execucao=5,
        modo_sombra=True,
    )

    ofertas = scraper.buscar_ofertas(limite=5)

    assert ofertas == []

    estado = next(iter(processamentos.estados.values()))

    assert estado["status"] == "sombra_fora_nicho"


def test_modo_normal_emite_sem_terminal_ate_ack():
    processamentos = ProcessamentosFake()

    scraper = SocialScoutScraper(
        repository=RepositoryFake(
            [
                mensagem(1),
            ]
        ),
        processamentos_repository=processamentos,
        detector=DetectorFake(),
        resolvedor=ResolvedorFake(),
        validador_preco=ValidadorFake(),
        construtor=ConstrutorFake(),
        max_mensagens_por_execucao=5,
        modo_sombra=False,
    )

    ofertas = scraper.buscar_ofertas(limite=5)

    assert len(ofertas) == 1
    assert processamentos.quantidade() == 0

    assert scraper.confirmar_handoff(
        ofertas[0],
        status="pipeline_processada",
        motivo="teste",
    )

    estado = next(iter(processamentos.estados.values()))

    assert estado["status"] == "pipeline_processada"


def test_modo_sombra_respeita_limite_de_candidatas():
    processamentos = ProcessamentosFake()
    detector = DetectorFake()

    scraper = SocialScoutScraper(
        repository=RepositoryFake(
            [
                mensagem(1),
                mensagem(2),
                mensagem(3),
            ]
        ),
        processamentos_repository=processamentos,
        detector=detector,
        resolvedor=ResolvedorFake(),
        validador_preco=ValidadorFake(),
        construtor=ConstrutorFake(),
        max_mensagens_por_execucao=10,
        modo_sombra=True,
    )

    ofertas = scraper.buscar_ofertas(limite=1)

    assert ofertas == []

    assert detector.ids_processados == [3]

    assert processamentos.quantidade() == 1


def test_mensagem_consumida_em_sombra_nao_reaparece_ao_ir_para_normal():
    processamentos = ProcessamentosFake()

    msg = mensagem(
        1,
        texto="Mouse Gamer RGB Modelo Teste",
    )

    detector_sombra = DetectorFake()

    sombra = SocialScoutScraper(
        repository=RepositoryFake([msg]),
        processamentos_repository=processamentos,
        detector=detector_sombra,
        resolvedor=ResolvedorFake(),
        validador_preco=ValidadorFake(),
        construtor=ConstrutorFake(),
        modo_sombra=True,
    )

    assert sombra.buscar_ofertas() == []

    detector_normal = DetectorFake()

    normal = SocialScoutScraper(
        repository=RepositoryFake([msg]),
        processamentos_repository=processamentos,
        detector=detector_normal,
        resolvedor=ResolvedorFake(),
        validador_preco=ValidadorFake(),
        construtor=ConstrutorFake(),
        modo_sombra=False,
    )

    assert normal.buscar_ofertas() == []

    assert detector_sombra.ids_processados == [1]

    assert detector_normal.ids_processados == []


def test_limite_de_execucao_nao_bloqueia_backlog_atras_de_processadas():
    mensagens = [
        mensagem(1),
        mensagem(2),
        mensagem(3),
        mensagem(4),
    ]

    processamentos = ProcessamentosFake()

    detector_primeira = DetectorFake()

    primeira = SocialScoutScraper(
        repository=RepositoryFake(mensagens),
        processamentos_repository=processamentos,
        detector=detector_primeira,
        resolvedor=ResolvedorFake(),
        validador_preco=ValidadorFake(),
        construtor=ConstrutorFake(),
        max_mensagens_por_execucao=2,
        modo_sombra=False,
    )

    ofertas_primeira = primeira.buscar_ofertas(limite=10)

    assert len(ofertas_primeira) == 2

    assert detector_primeira.ids_processados == [
        4,
        3,
    ]

    for oferta in ofertas_primeira:
        assert primeira.confirmar_handoff(
            oferta,
            status="pipeline_processada",
            motivo="teste",
        )

    detector_segunda = DetectorFake()

    segunda = SocialScoutScraper(
        repository=RepositoryFake(mensagens),
        processamentos_repository=processamentos,
        detector=detector_segunda,
        resolvedor=ResolvedorFake(),
        validador_preco=ValidadorFake(),
        construtor=ConstrutorFake(),
        max_mensagens_por_execucao=2,
        modo_sombra=False,
    )

    ofertas_segunda = segunda.buscar_ofertas(limite=10)

    assert len(ofertas_segunda) == 2

    # As duas mais novas ja estavam terminais.
    # Elas nao podem consumir a cota do segundo ciclo.
    assert detector_segunda.ids_processados == [
        2,
        1,
    ]


def test_v3_shadow_rejeita_climatizacao_fora_escopo_social():
    processamentos = ProcessamentosFake()

    scraper = SocialScoutScraper(
        repository=RepositoryFake(
            [
                mensagem(
                    9001,
                    texto=("Ventilador de Torre WAP " "Air Silence"),
                ),
            ]
        ),
        processamentos_repository=processamentos,
        detector=DetectorFake(),
        resolvedor=ResolvedorFake(),
        validador_preco=ValidadorFake(),
        construtor=ConstrutorFake(),
        modo_sombra=True,
    )

    assert scraper.buscar_ofertas(limite=5) == []

    estado = next(iter(processamentos.estados.values()))

    assert estado["status"] == "sombra_fora_nicho"

    assert "fora_escopo_social_scout" in estado["motivo"]

    assert "Climatiza\u00e7\u00e3o e conforto" in estado["motivo"]


def test_v3_shadow_preserva_hardware_real():
    processamentos = ProcessamentosFake()

    scraper = SocialScoutScraper(
        repository=RepositoryFake(
            [
                mensagem(
                    9002,
                    texto=("Processador AMD " "Ryzen 7 5700X"),
                ),
            ]
        ),
        processamentos_repository=processamentos,
        detector=DetectorFake(),
        resolvedor=ResolvedorFake(),
        validador_preco=ValidadorFake(),
        construtor=ConstrutorFake(),
        modo_sombra=True,
    )

    assert scraper.buscar_ofertas(limite=5) == []

    estado = next(iter(processamentos.estados.values()))

    assert estado["status"] == "sombra_nicho"

    assert "Processador" in estado["motivo"]

    assert "fora_escopo_social_scout" not in estado["motivo"]


def test_v3_normal_nao_emite_climatizacao():
    processamentos = ProcessamentosFake()

    scraper = SocialScoutScraper(
        repository=RepositoryFake(
            [
                mensagem(
                    9003,
                    texto=("Ventilador de Torre WAP " "Air Silence"),
                ),
            ]
        ),
        processamentos_repository=processamentos,
        detector=DetectorFake(),
        resolvedor=ResolvedorFake(),
        validador_preco=ValidadorFake(),
        construtor=ConstrutorFake(),
        modo_sombra=False,
    )

    ofertas = scraper.buscar_ofertas(limite=5)

    assert ofertas == []

    assert processamentos.quantidade() == 1

    estado = next(iter(processamentos.estados.values()))

    assert estado["status"] == "fora_escopo"

    assert estado["motivo"] == (
        "categoria_fora_escopo_social_scout:" "Climatiza\u00e7\u00e3o e conforto"
    )


def test_v3_normal_preserva_handoff_de_hardware():
    processamentos = ProcessamentosFake()

    scraper = SocialScoutScraper(
        repository=RepositoryFake(
            [
                mensagem(
                    9004,
                    texto=("SSD NVMe Kingston " "1TB PCIe"),
                ),
            ]
        ),
        processamentos_repository=processamentos,
        detector=DetectorFake(),
        resolvedor=ResolvedorFake(),
        validador_preco=ValidadorFake(),
        construtor=ConstrutorFake(),
        modo_sombra=False,
    )

    ofertas = scraper.buscar_ofertas(limite=5)

    assert len(ofertas) == 1

    # Durable handoff:
    # nenhum estado terminal antes do ACK.
    assert processamentos.quantidade() == 0

    assert scraper.confirmar_handoff(
        ofertas[0],
        status="pipeline_processada",
        motivo="teste_v3",
    )

    assert processamentos.quantidade() == 1


def test_preco_nao_verificavel_vira_terminal_sem_retry():
    class ValidadorNaoVerificavelFake:
        def __init__(self):
            self.chamadas = 0

        def validar(
            self,
            deteccao,
            resolucao,
        ):
            self.chamadas += 1

            return ResultadoValidacaoPrecoSocialScout(
                status="nao_verificavel",
                marketplace="mercado_livre",
                url=resolucao.url_destino,
                titulo_oficial=deteccao.titulo,
                motivo=("mensagem_social_sem_preco_base"),
            )

    processamentos = ProcessamentosFake()

    validador = ValidadorNaoVerificavelFake()

    scraper = SocialScoutScraper(
        repository=RepositoryFake(
            [
                mensagem(
                    9101,
                    texto=("RTX 5060 Ti R$ 3799 " "- CUPOM: TESTE10"),
                ),
            ]
        ),
        processamentos_repository=processamentos,
        detector=DetectorFake(),
        resolvedor=ResolvedorFake(),
        validador_preco=validador,
        construtor=ConstrutorFake(),
        max_mensagens_por_execucao=5,
        modo_sombra=True,
    )

    assert scraper.buscar_ofertas(limite=5) == []

    assert validador.chamadas == 1
    assert processamentos.quantidade() == 1

    estado = next(iter(processamentos.estados.values()))

    assert estado["status"] == "preco_nao_verificavel"

    assert scraper.buscar_ofertas(limite=5) == []

    assert validador.chamadas == 1
    assert processamentos.quantidade() == 1


class ProcessadorShopeeV4Fake:
    def __init__(self):
        self.resolucoes = 0
        self.validacoes = 0

    def resolver(
        self,
        msg,
        deteccao,
    ):
        self.resolucoes += 1

        return ResultadoResolucaoSocialScout(
            fonte=msg.fonte,
            id_externo=(f"{msg.chat_id}:" f"{msg.message_id}"),
            status="resolvido",
            marketplace="shopee",
            tipo_destino="produto",
            url_original=msg.links[0],
            url_destino=("https://shopee.com.br/" "product/10/123"),
            id_produto="123",
            id_anuncio="123",
            motivo="teste_v4",
        )

    def validar(
        self,
        deteccao,
        resolucao,
    ):
        self.validacoes += 1

        return ResultadoValidacaoPrecoSocialScout(
            status="validado",
            marketplace="shopee",
            url=resolucao.url_destino,
            titulo_oficial=deteccao.titulo,
            preco_oficial=100.00,
            preco_original_oficial=200.00,
            preco_oferta_grupo=100.00,
            preco_base_confere=True,
            motivo="teste_v4",
        )


def test_v4_rota_shopee_para_processador_especifico():
    processamentos = ProcessamentosFake()
    resolvedor_ml = ResolvedorFake()
    processador_shopee = ProcessadorShopeeV4Fake()

    scraper = SocialScoutScraper(
        repository=RepositoryFake(
            [
                mensagem(
                    9401,
                    texto=("Mouse Gamer Logitech G305"),
                ),
            ]
        ),
        processamentos_repository=processamentos,
        detector=DetectorFake(marketplace="shopee"),
        resolvedor=resolvedor_ml,
        validador_preco=ValidadorFake(),
        processador_shopee=(processador_shopee),
        construtor=ConstrutorFake(),
        modo_sombra=False,
    )

    ofertas = scraper.buscar_ofertas(limite=5)

    assert len(ofertas) == 1

    assert processador_shopee.resolucoes == 1

    assert processador_shopee.validacoes == 1

    assert resolvedor_ml.chamadas == 0

    assert SocialScoutScraper.VERSAO_PROCESSADOR == "5"
