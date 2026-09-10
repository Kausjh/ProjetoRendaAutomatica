from __future__ import annotations

import os

DEFAULT_LIMITES_HUNTER_POR_FONTE: dict[str, int] = {
    "MercadoLivreScraper": 10,
    "ShopeeScraper": 10,
    "KabumScraper": 10,
    "AliExpressScraper": 5,
    "SocialScoutScraper": 5,
}


VARIAVEIS_LIMITE_HUNTER: dict[str, str] = {
    "MercadoLivreScraper": "HUNTER_LIMITE_MERCADO_LIVRE",
    "ShopeeScraper": "HUNTER_LIMITE_SHOPEE",
    "KabumScraper": "HUNTER_LIMITE_KABUM",
    "AliExpressScraper": "HUNTER_LIMITE_ALIEXPRESS",
    "SocialScoutScraper": "HUNTER_LIMITE_SOCIAL_SCOUT",
}


def carregar_limites_hunter_por_fonte() -> dict[str, int]:
    limites: dict[str, int] = {}

    for fonte, limite_padrao in DEFAULT_LIMITES_HUNTER_POR_FONTE.items():
        variavel = VARIAVEIS_LIMITE_HUNTER[fonte]

        bruto = os.getenv(variavel)

        if bruto is None or not bruto.strip():
            limite = limite_padrao

        else:
            try:
                limite = int(bruto)

            except ValueError as erro:
                raise ValueError(f"{variavel} precisa ser um numero inteiro.") from erro

        if limite <= 0:
            raise ValueError(f"{variavel} precisa ser maior que zero.")

        limites[fonte] = limite

    return limites
