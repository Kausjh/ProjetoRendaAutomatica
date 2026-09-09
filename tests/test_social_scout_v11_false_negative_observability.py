# 63.8738, -149.7525

from models.mensagem_social_scout import (
    MensagemSocialScout,
)
from models.resultado_resolucao_social_scout import (
    ResultadoResolucaoSocialScout,
)
from scrapers.social_scout_scraper import (
    SocialScoutScraper,
)
from services.scout.detector_promocao_social_scout import (
    DetectorPromocaoSocialScout,
)


def mensagem(
    *,
    texto: str,
    links: tuple[str, ...],
    message_id: int = 1,
):
    return MensagemSocialScout(
        fonte="telegram",
        chat_id="-1000000000000",
        message_id=message_id,
        chat_titulo="Grupo Teste",
        texto=texto,
        links=links,
    )


def test_v11_kabum_nao_e_contaminada_por_amazon_prime():
    resultado = DetectorPromocaoSocialScout.detectar(
        mensagem(
            texto=(
                "ALERTA de Cupom kabum!\n" "R$ 100 OFF em R$ 1000\n" "Amazon prime 30 dias gratis"
            ),
            links=(
                "https://exemplo.invalid/kabum-curto",
                "https://www.amazon.com.br/prime",
            ),
        )
    )

    assert resultado.marketplace == "kabum"


def test_v11_link_suportado_vence_footer_amazon():
    resultado = DetectorPromocaoSocialScout.detectar(
        mensagem(
            texto=("Monitor Gamer 27\n" "Por: R$ 625,00"),
            links=(
                "https://www.amazon.com.br/prime",
                ("https://shopee.com.br/" "product/10/123"),
            ),
        )
    )

    assert resultado.marketplace == "shopee"


def test_v11_amazon_pura_continua_amazon():
    resultado = DetectorPromocaoSocialScout.detectar(
        mensagem(
            texto=("Monitor AOC 27 4K\n" "Por: R$ 999,00"),
            links=("https://www.amazon.com.br/dp/TESTE",),
        )
    )

    assert resultado.marketplace == "amazon"


class RepositoryFake:
    def __init__(self, mensagens):
        self.mensagens = list(mensagens)

    def listar(self):
        return list(self.mensagens)


class ProcessamentosFake:
    def __init__(self):
        self.registros = []

    def esta_processada(
        self,
        *args,
        **kwargs,
    ):
        return False

    def salvar(
        self,
        **kwargs,
    ):
        self.registros.append(dict(kwargs))


class ShopeeNaoResolveFake:
    def resolver(
        self,
        mensagem,
        deteccao,
    ):
        return ResultadoResolucaoSocialScout(
            fonte=mensagem.fonte,
            id_externo="teste:v11",
            status="nao_suportado",
            marketplace="shopee",
            motivo="teste_rejeicao_shopee",
        )


def criar_scraper_shadow(
    mensagem_alvo,
    processamentos,
):
    return SocialScoutScraper(
        repository=RepositoryFake([mensagem_alvo]),
        processamentos_repository=(processamentos),
        detector=(DetectorPromocaoSocialScout()),
        resolvedor=object(),
        validador_preco=object(),
        processador_shopee=(ShopeeNaoResolveFake()),
        processador_aliexpress=object(),
        processador_kabum=object(),
        construtor=object(),
        max_mensagens_por_execucao=5,
        modo_sombra=True,
    )


def test_v11_shadow_prevalidacao_enxerga_cpu_antes_da_rejeicao():
    alvo = mensagem(
        texto=("Processador AMD Ryzen 7 5700\n" "Por: R$ 648,00"),
        links=("https://shopee.com.br/product/10/123",),
        message_id=11,
    )

    processamentos = ProcessamentosFake()

    scraper = criar_scraper_shadow(
        alvo,
        processamentos,
    )

    assert scraper.buscar_ofertas(limite=5) == []

    assert len(processamentos.registros) == 1

    registro = processamentos.registros[0]

    # A trava real continua existindo.
    assert registro["status"] == "nao_resolvida"

    assert "teste_rejeicao_shopee" in registro["motivo"]

    # Mas agora sabemos que perdemos
    # uma oferta pertencente ao nicho.
    assert "shadow_pre=nicho" in registro["motivo"]

    assert "categoria=Processador" in registro["motivo"]


def test_v11_modo_normal_nao_cria_observacao_shadow():
    alvo = mensagem(
        texto=("Processador AMD Ryzen 7 5700\n" "Por: R$ 648,00"),
        links=("https://shopee.com.br/product/10/123",),
        message_id=12,
    )

    scraper = SocialScoutScraper(
        repository=RepositoryFake([alvo]),
        processamentos_repository=(ProcessamentosFake()),
        detector=(DetectorPromocaoSocialScout()),
        resolvedor=object(),
        validador_preco=object(),
        processador_shopee=object(),
        processador_aliexpress=object(),
        processador_kabum=object(),
        construtor=object(),
        modo_sombra=False,
    )

    deteccao = DetectorPromocaoSocialScout.detectar(alvo)

    scraper._preparar_sombra_prevalidacao(
        mensagem=alvo,
        deteccao=deteccao,
        fingerprint="teste",
    )

    assert scraper._sombra_prevalidacao_por_fingerprint == {}


def test_v11_versao_processador():
    assert int(SocialScoutScraper.VERSAO_PROCESSADOR) >= 11
