import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from playwright.sync_api import sync_playwright


class CookieManager:

    def __init__(
        self,
        cdp_url: str = "http://127.0.0.1:9222",
        duracao_cache_segundos: int = 1800,
    ) -> None:

        self.cdp_url = cdp_url
        self.duracao_cache_segundos = (
            duracao_cache_segundos
        )

        self._cookies_cache: dict[
            str,
            str
        ] | None = None

        self._momento_cache = 0.0

        self._lock_cache = Lock()

        self._executor_playwright = (
            ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix=(
                    "cookie-manager-playwright"
                ),
            )
        )

    def obter_cookies(
        self,
        dominio: str = "mercadolivre.com.br",
        forcar_atualizacao: bool = False,
    ) -> dict[str, str]:

        with self._lock_cache:

            if (
                not forcar_atualizacao
                and self._cache_valido()
            ):
                return dict(
                    self._cookies_cache or {}
                )

            cookies = (
                self._extrair_cookies_em_thread(
                    dominio=dominio
                )
            )

            if not cookies:
                raise RuntimeError(
                    "Nenhum cookie do Mercado Livre "
                    "foi encontrado no Chrome conectado "
                    "pela porta CDP 9222."
                )

            self._cookies_cache = cookies
            self._momento_cache = time.monotonic()

            return dict(cookies)

    def invalidar_cache(
        self
    ) -> None:

        with self._lock_cache:
            self._cookies_cache = None
            self._momento_cache = 0.0

    def _cache_valido(
        self
    ) -> bool:

        if self._cookies_cache is None:
            return False

        tempo_decorrido = (
            time.monotonic()
            - self._momento_cache
        )

        return (
            tempo_decorrido
            < self.duracao_cache_segundos
        )

    def _extrair_cookies_em_thread(
        self,
        dominio: str,
    ) -> dict[str, str]:

        tarefa = self._executor_playwright.submit(
            self._extrair_cookies,
            dominio,
        )

        return tarefa.result()

    def _extrair_cookies(
        self,
        dominio: str,
    ) -> dict[str, str]:

        # O Playwright síncrono precisa rodar fora da thread
        # que mantém o loop asyncio principal do projeto.
        # 63.8738, -149.7525
        with sync_playwright() as playwright:

            navegador = (
                playwright.chromium.connect_over_cdp(
                    self.cdp_url
                )
            )

            if not navegador.contexts:
                raise RuntimeError(
                    "O Chrome conectado pela porta "
                    "9222 não possui nenhum contexto."
                )

            resultado: dict[str, str] = {}

            for contexto in navegador.contexts:

                cookies = contexto.cookies()

                for cookie in cookies:

                    dominio_cookie = str(
                        cookie.get(
                            "domain",
                            ""
                        )
                    )

                    if dominio not in dominio_cookie:
                        continue

                    nome = str(
                        cookie.get(
                            "name",
                            ""
                        )
                    )

                    valor = str(
                        cookie.get(
                            "value",
                            ""
                        )
                    )

                    if not nome:
                        continue

                    resultado[nome] = valor

            return resultado
