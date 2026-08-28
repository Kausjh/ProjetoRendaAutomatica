import logging

from affiliates.afiliador_generico import AfiliadorGenerico
from affiliates.afiliador_mercado_livre import (
    AfiliadorMercadoLivre,
)
from affiliates.afiliador_parametros import AfiliadorParametros
from affiliates.afiliador_shopee import AfiliadorShopee
from affiliates.base_afiliador import BaseAfiliador
from affiliates.carregador_afiliadores import (
    CarregadorAfiliadores,
)
from affiliates.configuracao_afiliador import (
    ConfiguracaoAfiliador,
)
from affiliates.gerador_link_afiliado import GeradorLinkAfiliado
from config.configuracoes import Configuracoes
from config.configuracoes_afiliados import ConfiguracoesAfiliados

logger = logging.getLogger(__name__)

# 63.8738, -149.7525


def criar_gerador_link_afiliado(
    configuracoes: Configuracoes,
) -> GeradorLinkAfiliado:
    del configuracoes

    configuracoes_afiliados = ConfiguracoesAfiliados()

    carregador = CarregadorAfiliadores(caminho_arquivo=configuracoes_afiliados.caminho_arquivo)

    afiliadores_configurados = carregador.carregar()

    gerador = GeradorLinkAfiliado()

    quantidade_registrada = 0
    quantidade_desativada = 0

    for configuracao in afiliadores_configurados:
        if not configuracao.ativo:
            quantidade_desativada += 1

            logger.info(
                "Afiliador desativado ignorado: %s.",
                configuracao.nome,
            )

            continue

        afiliador = _criar_afiliador(configuracao)

        gerador.registrar(afiliador)

        quantidade_registrada += 1

        logger.info(
            ("Afiliador registrado: %s | " "Tipo: %s | Prioridade: %s | " "Dom?nios: %s"),
            configuracao.nome,
            configuracao.tipo,
            configuracao.prioridade,
            ", ".join(configuracao.dominios),
        )

    gerador.registrar(AfiliadorGenerico())

    logger.info(
        (
            "Registro de afiliadores conclu?do. "
            "Ativos: %s | Desativados: %s | "
            "Fallback: ativo."
        ),
        quantidade_registrada,
        quantidade_desativada,
    )

    return gerador


def _criar_afiliador(
    configuracao: ConfiguracaoAfiliador,
) -> BaseAfiliador:
    if configuracao.tipo == "mercado_livre":
        return AfiliadorMercadoLivre(
            nome=configuracao.nome,
            dominios=configuracao.dominios,
        )

    if configuracao.tipo == "shopee":
        return AfiliadorShopee(
            nome=configuracao.nome,
            dominios=configuracao.dominios,
        )

    if configuracao.tipo == "parametros":
        return AfiliadorParametros(
            nome=configuracao.nome,
            dominios=configuracao.dominios,
            parametros=configuracao.parametros,
        )

    raise ValueError("Tipo de afiliador n?o implementado: " f"'{configuracao.tipo}'.")
