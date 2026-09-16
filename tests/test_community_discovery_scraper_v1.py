from types import SimpleNamespace

from scrapers.community_discovery_scraper import (
    CommunityDiscoveryScraper,
)


class QueueFake:
    def __init__(self, reservadas=()):
        self.reservadas = list(reservadas)
        self.limites = []
        self.aprovacoes = []
        self.rejeicoes = []
        self.erros = []

    def reservar(self, *, limite):
        self.limites.append(limite)
        return self.reservadas[:limite]

    def aprovar(self, descoberta_id, *, canonical_key=None, motivo=None):
        self.aprovacoes.append((descoberta_id, canonical_key, motivo))

    def rejeitar(self, descoberta_id, *, motivo):
        self.rejeicoes.append((descoberta_id, motivo))

    def registrar_erro(self, descoberta_id, *, erro, transitorio=True):
        self.erros.append((descoberta_id, str(erro), transitorio))


class AdapterFake:
    def __init__(self, resultados):
        self.resultados = resultados
        self.chamadas = []

    def processar(self, descoberta):
        self.chamadas.append(descoberta.id)
        resultado = self.resultados[descoberta.id]
        if isinstance(resultado, Exception):
            raise resultado
        return resultado


def descoberta(identificador):
    return SimpleNamespace(id=identificador, status="processing")


def oferta(canonical_key=None):
    return SimpleNamespace(chave_produto_canonica=canonical_key)


def resultado(*, status, oferta_atual=None, motivo="teste", transitorio=False):
    return SimpleNamespace(
        status=status,
        oferta=oferta_atual,
        motivo=motivo,
        transitorio=transitorio,
    )


def test_oferta_so_aprova_depois_do_ack_pipeline():
    item = descoberta("dsc_1")
    oferta_atual = oferta("canon:123")
    fila = QueueFake([item])
    adapter = AdapterFake(
        {
            item.id: resultado(
                status="oferta_criada",
                oferta_atual=oferta_atual,
            ),
        }
    )
    scraper = CommunityDiscoveryScraper(queue_service=fila, adapter=adapter)

    ofertas = scraper.buscar_ofertas(limite=5)

    assert ofertas == [oferta_atual]
    assert fila.aprovacoes == []
    assert fila.rejeicoes == []
    assert fila.erros == []

    assert scraper.confirmar_handoff(
        oferta_atual,
        status="pipeline_processada",
        motivo="ciclo_pipeline_concluido_com_sucesso",
    )

    assert fila.aprovacoes == [
        (
            "dsc_1",
            "canon:123",
            "pipeline_processada:ciclo_pipeline_concluido_com_sucesso",
        )
    ]

    assert not scraper.confirmar_handoff(
        oferta_atual,
        status="pipeline_processada",
        motivo="repetido",
    )


def test_duplicata_downstream_e_terminal_aprovada():
    item = descoberta("dsc_dup")
    oferta_atual = oferta()
    fila = QueueFake([item])
    adapter = AdapterFake({item.id: resultado(status="oferta_criada", oferta_atual=oferta_atual)})
    scraper = CommunityDiscoveryScraper(queue_service=fila, adapter=adapter)

    [emitida] = scraper.buscar_ofertas(limite=1)

    assert scraper.confirmar_handoff(
        emitida,
        status="coletor_duplicada",
        motivo="link_duplicado_no_coletor",
    )
    assert fila.aprovacoes[0][0] == "dsc_dup"
    assert fila.rejeicoes == []


def test_rejeicao_terminal_do_coletor_rejeita_fila():
    item = descoberta("dsc_fora_nicho")
    oferta_atual = oferta()
    fila = QueueFake([item])
    adapter = AdapterFake({item.id: resultado(status="oferta_criada", oferta_atual=oferta_atual)})
    scraper = CommunityDiscoveryScraper(queue_service=fila, adapter=adapter)

    [emitida] = scraper.buscar_ofertas(limite=1)

    assert scraper.confirmar_handoff(
        emitida,
        status="coletor_fora_nicho",
        motivo="fora_do_nicho",
    )
    assert fila.aprovacoes == []
    assert fila.rejeicoes == [("dsc_fora_nicho", "coletor_fora_nicho:fora_do_nicho")]


def test_adapter_retry_volta_para_state_machine():
    item = descoberta("dsc_retry")
    fila = QueueFake([item])
    adapter = AdapterFake(
        {
            item.id: resultado(
                status="retry",
                motivo="timeout_marketplace",
                transitorio=True,
            ),
        }
    )
    scraper = CommunityDiscoveryScraper(queue_service=fila, adapter=adapter)

    assert scraper.buscar_ofertas(limite=5) == []
    assert fila.erros == [("dsc_retry", "timeout_marketplace", True)]


def test_adapter_nao_suportado_rejeita_sem_emitir():
    item = descoberta("dsc_amazon")
    fila = QueueFake([item])
    adapter = AdapterFake(
        {
            item.id: resultado(
                status="nao_suportada",
                motivo="amazon_sem_processador_de_produto",
            ),
        }
    )
    scraper = CommunityDiscoveryScraper(queue_service=fila, adapter=adapter)

    assert scraper.buscar_ofertas(limite=5) == []
    assert fila.rejeicoes == [("dsc_amazon", "amazon_sem_processador_de_produto")]


def test_excecao_adapter_registra_retry_sem_perder_item():
    item = descoberta("dsc_exception")
    fila = QueueFake([item])
    adapter = AdapterFake({item.id: RuntimeError("boom")})
    scraper = CommunityDiscoveryScraper(queue_service=fila, adapter=adapter)

    assert scraper.buscar_ofertas(limite=5) == []
    assert fila.erros == [
        (
            "dsc_exception",
            "community_discovery_adapter_exception:RuntimeError",
            True,
        )
    ]


def test_limite_externo_respeita_teto_do_worker():
    itens = [
        descoberta("dsc_1"),
        descoberta("dsc_2"),
        descoberta("dsc_3"),
    ]
    fila = QueueFake(itens)
    adapter = AdapterFake(
        {item.id: resultado(status="rejeitada", motivo="teste") for item in itens}
    )
    scraper = CommunityDiscoveryScraper(
        queue_service=fila,
        adapter=adapter,
        max_descobertas_por_execucao=2,
    )

    scraper.buscar_ofertas(limite=50)

    assert fila.limites == [2]
    assert adapter.chamadas == ["dsc_1", "dsc_2"]
