from services.scout.processador_aliexpress_social_scout import (
    ProcessadorAliExpressSocialScout,
)

PRODUTO_ID = "1005013172770880"


def _produto_id(url: str) -> str | None:
    return ProcessadorAliExpressSocialScout._produto_id_url(url)


def test_produto_id_url_preserva_item_direto() -> None:
    url = f"https://www.aliexpress.com/item/{PRODUTO_ID}.html"

    assert _produto_id(url) == PRODUTO_ID


def test_produto_id_url_reconhece_coin_index_com_productids() -> None:
    url = (
        "https://m.aliexpress.com/p/coin-index/index.html"
        f"?productIds={PRODUTO_ID}"
        "&aff_platform=api-new-link-generate"
    )

    assert _produto_id(url) == PRODUTO_ID


def test_produto_id_url_coin_index_aceita_barra_final() -> None:
    url = "https://m.aliexpress.com/p/coin-index/index.html/" f"?productIds={PRODUTO_ID}"

    assert _produto_id(url) == PRODUTO_ID


def test_produto_id_url_coin_index_sem_productids_nao_e_produto() -> None:
    url = "https://www.aliexpress.com/p/coin-index/index.html"

    assert _produto_id(url) is None


def test_produto_id_url_coin_index_rejeita_productids_repetido() -> None:
    url = (
        "https://m.aliexpress.com/p/coin-index/index.html"
        f"?productIds={PRODUTO_ID}"
        "&productIds=1005000000000000"
    )

    assert _produto_id(url) is None


def test_produto_id_url_coin_index_rejeita_id_nao_numerico() -> None:
    url = "https://m.aliexpress.com/p/coin-index/index.html" "?productIds=abc123"

    assert _produto_id(url) is None


def test_produto_id_url_nao_aceita_productids_em_path_arbitrario() -> None:
    url = "https://m.aliexpress.com/p/outra-pagina/index.html" f"?productIds={PRODUTO_ID}"

    assert _produto_id(url) is None


def test_produto_id_url_nao_aceita_productids_fora_do_aliexpress() -> None:
    url = "https://example.com/p/coin-index/index.html" f"?productIds={PRODUTO_ID}"

    assert _produto_id(url) is None
