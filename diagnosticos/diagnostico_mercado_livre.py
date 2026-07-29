from __future__ import annotations

import sys
import traceback

from repositories.links_afiliados_mercado_livre_repository import (
    LinksAfiliadosMercadoLivreRepository,
)
from services.browser.cookie_manager import CookieManager
from services.identificador_mercado_livre import IdentificadorMercadoLivre
from services.mercadolivre_affiliate_service import MercadoLivreAffiliateService

# 63.8738, -149.7525


def main() -> int:
    print("=" * 70)
    print("DIAGNÓSTICO DIRETO — AFILIADOS MERCADO LIVRE")
    print("=" * 70)

    link = " ".join(sys.argv[1:]).strip()

    if not link:
        link = input(
            "\nCole um link REAL de produto do Mercado Livre e pressione Enter:\n> "
        ).strip()

    if not link:
        print("\nERRO: nenhum link foi informado.")
        return 1

    identificador = IdentificadorMercadoLivre()
    identificacao = identificador.identificar(link)

    print("\n[1] IDENTIFICAÇÃO DO LINK")
    print(f"Domínio: {identificacao.dominio or 'não identificado'}")
    print(f"ID do produto: {identificacao.id_produto or 'não identificado'}")
    print(f"ID do anúncio: {identificacao.id_anuncio or 'não identificado'}")
    print(f"Já é meli.la: {identificacao.eh_link_afiliado}")

    if identificacao.eh_link_afiliado:
        print("\nO link informado já é um link afiliado meli.la.")
        return 0

    if "mercadolivre.com.br" not in identificacao.dominio:
        print("\nERRO: o link não pertence ao Mercado Livre Brasil.")
        return 1

    print("\n[2] LEITURA DOS COOKIES DO CHROME")

    cookie_manager = CookieManager()

    try:
        cookies = cookie_manager.obter_cookies(forcar_atualizacao=True)
    except Exception as erro:
        print("ERRO AO OBTER COOKIES: " f"{type(erro).__name__}: {erro}")
        traceback.print_exc()
        return 1

    print(f"Quantidade de cookies encontrados: {len(cookies)}")

    nomes_cookies = sorted(cookies.keys())

    if nomes_cookies:
        print("Nomes dos cookies encontrados: " + ", ".join(nomes_cookies))
    else:
        print("Nenhum cookie foi encontrado.")

    print("\n[3] TESTE DIRETO DA API DE AFILIADOS")

    servico = MercadoLivreAffiliateService(cookie_manager=cookie_manager)

    try:
        link_afiliado = servico.gerar(link)
    except Exception as erro:
        print("ERRO NA CHAMADA DA API: " f"{type(erro).__name__}: {erro}")
        traceback.print_exc()
        return 1

    if not link_afiliado:
        print("\nRESULTADO: FALHOU.")
        print(
            "A API não devolveu um link https://meli.la/. "
            "Veja acima o código HTTP ou a mensagem de erro."
        )
        return 2

    print("\nRESULTADO: SUCESSO.")
    print(f"Link afiliado gerado: {link_afiliado}")

    print("\n[4] TESTE DO REPOSITÓRIO E CACHE")

    try:
        repositorio = LinksAfiliadosMercadoLivreRepository()
        registro = repositorio.cadastrar(
            link_original=link,
            link_afiliado=link_afiliado,
        )
    except ValueError as erro:
        print("AVISO: o link foi gerado corretamente, mas não pôde " f"ser salvo no cache: {erro}")
        print("A monetização funciona, mas o identificador/cache " "ainda precisa ser corrigido.")
        return 0
    except Exception as erro:
        print("ERRO AO SALVAR NO CACHE: " f"{type(erro).__name__}: {erro}")
        traceback.print_exc()
        return 1

    print(f"Item salvo: {registro.item_id}")
    print(f"Cache salvo em: {repositorio.caminho_arquivo}")
    print("\nDIAGNÓSTICO CONCLUÍDO COM SUCESSO.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
