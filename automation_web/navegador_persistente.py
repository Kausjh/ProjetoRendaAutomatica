from types import TracebackType
from typing import Self

from playwright.sync_api import (
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
)

from automation_web.configuracao_navegador import ConfiguracaoNavegador


class NavegadorPersistente:
    """Gerencia um navegador dedicado com sessão persistida em disco."""

    def __init__(
        self,
        configuracao: ConfiguracaoNavegador | None = None,
    ) -> None:
        self.configuracao = (
            configuracao if configuracao is not None else ConfiguracaoNavegador.padrao()
        )

        self._playwright: Playwright | None = None
        self._contexto: BrowserContext | None = None

    @property
    def contexto(self) -> BrowserContext:
        if self._contexto is None:
            raise RuntimeError(
                "O navegador ainda não foi iniciado. " "Use iniciar() ou o bloco 'with'."
            )

        return self._contexto

    @property
    def pagina(self) -> Page:
        paginas = self.contexto.pages

        if paginas:
            return paginas[0]

        return self.contexto.new_page()

    def iniciar(self) -> Self:
        if self._contexto is not None:
            return self

        self.configuracao.preparar_diretorios()
        self._playwright = sync_playwright().start()

        try:
            self._contexto = self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.configuracao.pasta_perfil),
                headless=self.configuracao.headless,
                viewport=(
                    {
                        "width": self.configuracao.largura_viewport,
                        "height": self.configuracao.altura_viewport,
                    }
                    if (
                        self.configuracao.largura_viewport is not None
                        and self.configuracao.altura_viewport is not None
                    )
                    else None
                ),
                args=[
                    "--start-maximized",
                ],
            )

            self._contexto.set_default_timeout(self.configuracao.timeout_padrao_ms)

            self._contexto.set_default_navigation_timeout(self.configuracao.timeout_navegacao_ms)

        except Exception:
            self.fechar()
            raise

        return self

    def nova_pagina(self) -> Page:
        return self.contexto.new_page()

    def fechar(self) -> None:
        if self._contexto is not None:
            try:
                self._contexto.close()
            finally:
                self._contexto = None

        if self._playwright is not None:
            try:
                self._playwright.stop()
            finally:
                self._playwright = None

    def __enter__(self) -> Self:
        return self.iniciar()

    def __exit__(
        self,
        tipo_erro: type[BaseException] | None,
        erro: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.fechar()
