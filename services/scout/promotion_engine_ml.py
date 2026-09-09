# 63.8738, -149.7525

from __future__ import annotations

import re
from dataclasses import dataclass

from playwright.sync_api import (
    Error as PlaywrightError,
)
from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
)
from playwright.sync_api import (
    sync_playwright,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ResultadoPromocaoMarketplace:
    status: str

    marketplace: str = "mercado_livre"
    id_produto: str | None = None

    promocao_confirmada: bool = False
    tipo_promocao: str | None = None

    preco_base: float | None = None
    preco_promocional: float | None = None

    valor_desconto: float | None = None
    desconto_percentual: float | None = None

    preco_grupo: float | None = None
    preco_grupo_confere: bool | None = None

    # IMPORTANTE:
    # reconhecer uma promocao no marketplace nao prova
    # qual codigo de cupom produz aquela promocao.
    codigo_cupom_validado: bool = False

    fonte_url: str | None = None
    evidencia: str = ""
    motivo: str = ""


class PromotionEngineMercadoLivre:
    """Inspeciona promocoes exibidas oficialmente pelo ML.

    V1 e totalmente passiva.

    Nao:
    - aplica cupom;
    - resgata cupom;
    - altera carrinho;
    - inicia compra.

    A identidade e sempre ancorada pelo id_produto exato.
    """

    MARKETPLACE = "mercado_livre"

    STATUS_CONFIRMADA = "confirmada"
    STATUS_SEM_EVIDENCIA = "sem_evidencia"
    STATUS_ERRO = "erro"

    ENDPOINT_CDP = "http://127.0.0.1:9222"

    def __init__(
        self,
        endpoint_cdp: str | None = None,
    ) -> None:
        self.endpoint_cdp = str(endpoint_cdp or self.ENDPOINT_CDP).strip()

        # Conexao CDP reutilizavel.
        # O Chrome compartilhado nunca e fechado aqui.
        self._playwright = None
        self._browser = None
        self._contexto = None

    def inspecionar(
        self,
        *,
        url_fonte: str,
        id_produto: str,
        preco_oficial: float | None,
        preco_final_grupo: float | None = None,
    ) -> ResultadoPromocaoMarketplace:
        identificador = str(id_produto or "").strip().upper()

        url = str(url_fonte or "").strip()

        if not identificador:
            return self._sem_evidencia(
                id_produto=None,
                fonte_url=url or None,
                preco_base=preco_oficial,
                preco_grupo=preco_final_grupo,
                motivo="id_produto_ausente",
            )

        if not url:
            return self._sem_evidencia(
                id_produto=identificador,
                fonte_url=None,
                preco_base=preco_oficial,
                preco_grupo=preco_final_grupo,
                motivo="url_fonte_ausente",
            )

        try:
            card = self._capturar_card(
                url_fonte=url,
                id_produto=identificador,
            )

        except PlaywrightError as erro:
            return ResultadoPromocaoMarketplace(
                status=self.STATUS_ERRO,
                id_produto=identificador,
                preco_base=self._preco(preco_oficial),
                preco_grupo=self._preco(preco_final_grupo),
                fonte_url=url,
                motivo=("erro_playwright:" + type(erro).__name__),
            )

        except Exception as erro:
            return ResultadoPromocaoMarketplace(
                status=self.STATUS_ERRO,
                id_produto=identificador,
                preco_base=self._preco(preco_oficial),
                preco_grupo=self._preco(preco_final_grupo),
                fonte_url=url,
                motivo=("erro_promocao:" + type(erro).__name__),
            )

        if card is None:
            return self._sem_evidencia(
                id_produto=identificador,
                fonte_url=url,
                preco_base=preco_oficial,
                preco_grupo=preco_final_grupo,
                motivo=("card_exato_nao_encontrado"),
            )

        return self.analisar_texto_card(
            texto_card=str(card.get("texto") or ""),
            id_produto=identificador,
            preco_oficial=preco_oficial,
            preco_final_grupo=preco_final_grupo,
            fonte_url=str(card.get("url_final") or url),
        )

    def analisar_texto_card(
        self,
        *,
        texto_card: str,
        id_produto: str,
        preco_oficial: float | None,
        preco_final_grupo: float | None = None,
        fonte_url: str | None = None,
    ) -> ResultadoPromocaoMarketplace:
        texto = self._normalizar(texto_card)

        identificador = str(id_produto or "").strip().upper()

        preco_base = self._preco(preco_oficial)

        preco_grupo = self._preco(preco_final_grupo)

        if "cupom" not in texto.casefold():
            return self._sem_evidencia(
                id_produto=identificador,
                fonte_url=fonte_url,
                preco_base=preco_base,
                preco_grupo=preco_grupo,
                evidencia=texto,
                motivo="card_exato_sem_cupom",
            )

        # --------------------------------------------------------
        # 1. PRECO FINAL EXPLICITO:
        # "R$ 3.470 com Cupom"
        # --------------------------------------------------------

        match_preco = re.search(
            r"R\$\s*" r"([\d.]+(?:\s*,\s*\d{1,2})?)" r"\s+com\s+Cupom",
            texto,
            flags=re.IGNORECASE,
        )

        if match_preco:
            preco_promocional = self._dinheiro_br(match_preco.group(1))

            if preco_promocional is not None:
                valor_desconto = None
                percentual = None

                if preco_base is not None and preco_promocional < preco_base:
                    valor_desconto = round(
                        preco_base - preco_promocional,
                        2,
                    )

                    percentual = round(
                        valor_desconto / preco_base * 100.0,
                        2,
                    )

                return self._confirmada(
                    id_produto=identificador,
                    tipo=("preco_final_com_cupom"),
                    preco_base=preco_base,
                    preco_promocional=(preco_promocional),
                    valor_desconto=(valor_desconto),
                    desconto_percentual=(percentual),
                    preco_grupo=preco_grupo,
                    fonte_url=fonte_url,
                    evidencia=texto,
                )

        # --------------------------------------------------------
        # 2. DESCONTO ABSOLUTO:
        # "R$ 60 OFF com Cupom"
        # --------------------------------------------------------

        match_valor = re.search(
            r"R\$\s*" r"([\d.]+(?:\s*,\s*\d{1,2})?)" r"\s+OFF\s+com\s+Cupom",
            texto,
            flags=re.IGNORECASE,
        )

        if match_valor:
            valor_desconto = self._dinheiro_br(match_valor.group(1))

            preco_promocional = None
            percentual = None

            if (
                valor_desconto is not None
                and preco_base is not None
                and valor_desconto < preco_base
            ):
                preco_promocional = round(
                    preco_base - valor_desconto,
                    2,
                )

                percentual = round(
                    valor_desconto / preco_base * 100.0,
                    2,
                )

            return self._confirmada(
                id_produto=identificador,
                tipo="valor_off_com_cupom",
                preco_base=preco_base,
                preco_promocional=(preco_promocional),
                valor_desconto=(valor_desconto),
                desconto_percentual=(percentual),
                preco_grupo=preco_grupo,
                fonte_url=fonte_url,
                evidencia=texto,
            )

        # --------------------------------------------------------
        # 3. PERCENTUAL:
        # "12% OFF com Cupom"
        # ou "Cupom 20% OFF"
        # --------------------------------------------------------

        match_percentual = re.search(
            r"(?:(\d{1,3}(?:[,.]\d+)?)%"
            r"\s+OFF\s+com\s+Cupom)"
            r"|(?:Cupom\s+"
            r"(\d{1,3}(?:[,.]\d+)?)%"
            r"\s+OFF)",
            texto,
            flags=re.IGNORECASE,
        )

        if match_percentual:
            bruto = match_percentual.group(1) or match_percentual.group(2)

            percentual = self._numero(bruto)

            preco_promocional = None
            valor_desconto = None

            if percentual is not None and preco_base is not None and 0 < percentual < 100:
                valor_desconto = round(
                    preco_base * percentual / 100.0,
                    2,
                )

                preco_promocional = round(
                    preco_base - valor_desconto,
                    2,
                )

            return self._confirmada(
                id_produto=identificador,
                tipo=("percentual_off_com_cupom"),
                preco_base=preco_base,
                preco_promocional=(preco_promocional),
                valor_desconto=(valor_desconto),
                desconto_percentual=(percentual),
                preco_grupo=preco_grupo,
                fonte_url=fonte_url,
                evidencia=texto,
            )

        # Marketplace confirma que existe cupom,
        # mas sem valor/preco interpretavel.
        return self._confirmada(
            id_produto=identificador,
            tipo="cupom_sem_valor_extraivel",
            preco_base=preco_base,
            preco_promocional=None,
            valor_desconto=None,
            desconto_percentual=None,
            preco_grupo=preco_grupo,
            fonte_url=fonte_url,
            evidencia=texto,
        )

    def _capturar_card(
        self,
        *,
        url_fonte: str,
        id_produto: str,
    ) -> dict | None:
        ultimo_erro: Exception | None = None

        # Uma conexao CDP pode sofrer falha transitoria.
        # Reconecta apenas uma vez antes de desistir.
        for tentativa in range(2):
            try:
                contexto = self._obter_contexto()

                return self._capturar_card_no_contexto(
                    contexto=contexto,
                    url_fonte=url_fonte,
                    id_produto=id_produto,
                )

            except PlaywrightError as erro:
                ultimo_erro = erro

                self._resetar_conexao()

                if tentativa == 0:
                    continue

                raise

        if ultimo_erro is not None:
            raise ultimo_erro

        return None

    def _obter_contexto(
        self,
    ):
        # Reaproveita a conexao ja criada.
        if self._browser is not None and self._contexto is not None:
            try:
                if self._browser.is_connected():
                    return self._contexto

            except Exception:
                pass

        self._resetar_conexao()

        self._playwright = sync_playwright().start()

        try:
            self._browser = self._playwright.chromium.connect_over_cdp(
                self.endpoint_cdp,
                timeout=30000,
            )

        except Exception:
            self._resetar_conexao()
            raise

        if not self._browser.contexts:
            self._resetar_conexao()

            raise RuntimeError("Chrome CDP sem contexto.")

        self._contexto = self._browser.contexts[0]

        return self._contexto

    def _capturar_card_no_contexto(
        self,
        *,
        contexto,
        url_fonte: str,
        id_produto: str,
    ) -> dict | None:
        pagina = contexto.new_page()

        pagina.set_default_timeout(10000)

        try:
            # Nao espera JS, imagens e recursos secundarios
            # terminarem. Precisamos apenas iniciar o documento.
            try:
                pagina.goto(
                    url_fonte,
                    wait_until="commit",
                    timeout=30000,
                )

            except PlaywrightTimeoutError:
                # Um timeout de navegacao nao invalida
                # automaticamente o DOM ja recebido.
                pass

            pagina.wait_for_timeout(2500)

            resultado = pagina.evaluate(
                """
                ({idProduto}) => {
                    const norm = (valor) => (
                        String(valor || "")
                            .replace(/\\s+/g, " ")
                            .trim()
                    );

                    const alvo = (
                        "/p/"
                        + idProduto
                    ).toLowerCase();

                    const anchors = Array.from(
                        document.querySelectorAll(
                            "a[href]"
                        )
                    );

                    const anchor = anchors.find(
                        a => (
                            String(
                                a.href || ""
                            )
                            .toLowerCase()
                            .includes(
                                alvo
                            )
                        )
                    );

                    if (!anchor) {
                        return null;
                    }

                    const card = anchor.closest(
                        ".poly-card"
                    );

                    if (!card) {
                        return null;
                    }

                    return {
                        texto: norm(
                            card.innerText
                        ),
                        href_produto:
                            anchor.href,
                        url_final:
                            location.href,
                    };
                }
                """,
                {
                    "idProduto": id_produto,
                },
            )

            return resultado

        finally:
            # Erro ao fechar aba auxiliar nunca deve
            # destruir um resultado valido.
            try:
                if not pagina.is_closed():
                    pagina.close(run_before_unload=False)

            except PlaywrightError:
                pass

    def _resetar_conexao(
        self,
    ) -> None:
        playwright = self._playwright

        self._contexto = None
        self._browser = None
        self._playwright = None

        if playwright is not None:
            try:
                # Desconecta somente o driver criado pelo
                # Promotion Engine.
                #
                # NAO executa browser.close(), portanto
                # nao fecha o Chrome real compartilhado.
                playwright.stop()

            except Exception:
                pass

    def fechar(
        self,
    ) -> None:
        self._resetar_conexao()

    def __enter__(
        self,
    ):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.fechar()

    def _confirmada(
        self,
        *,
        id_produto: str,
        tipo: str,
        preco_base: float | None,
        preco_promocional: float | None,
        valor_desconto: float | None,
        desconto_percentual: float | None,
        preco_grupo: float | None,
        fonte_url: str | None,
        evidencia: str,
    ) -> ResultadoPromocaoMarketplace:
        confere = None

        if preco_promocional is not None and preco_grupo is not None:
            confere = self._precos_conferem(
                preco_promocional,
                preco_grupo,
            )

        return ResultadoPromocaoMarketplace(
            status=self.STATUS_CONFIRMADA,
            id_produto=id_produto,
            promocao_confirmada=True,
            tipo_promocao=tipo,
            preco_base=preco_base,
            preco_promocional=(preco_promocional),
            valor_desconto=(valor_desconto),
            desconto_percentual=(desconto_percentual),
            preco_grupo=preco_grupo,
            preco_grupo_confere=confere,
            # V1 NAO valida codigo.
            codigo_cupom_validado=False,
            fonte_url=fonte_url,
            evidencia=(evidencia[:1200]),
            motivo=("promocao_oficial_no_" "card_exato_confirmada"),
        )

    def _sem_evidencia(
        self,
        *,
        id_produto: str | None,
        fonte_url: str | None,
        preco_base: float | None,
        preco_grupo: float | None,
        motivo: str,
        evidencia: str = "",
    ) -> ResultadoPromocaoMarketplace:
        return ResultadoPromocaoMarketplace(
            status=self.STATUS_SEM_EVIDENCIA,
            id_produto=id_produto,
            promocao_confirmada=False,
            preco_base=self._preco(preco_base),
            preco_grupo=self._preco(preco_grupo),
            preco_grupo_confere=None,
            codigo_cupom_validado=False,
            fonte_url=fonte_url,
            evidencia=evidencia[:1200],
            motivo=motivo,
        )

    @staticmethod
    def _normalizar(
        texto: str,
    ) -> str:
        return re.sub(
            r"\s+",
            " ",
            str(texto or ""),
        ).strip()

    @staticmethod
    def _numero(
        valor,
    ) -> float | None:
        if valor is None:
            return None

        bruto = (
            str(valor)
            .strip()
            .replace(
                ",",
                ".",
            )
        )

        try:
            numero = float(bruto)

        except (
            TypeError,
            ValueError,
        ):
            return None

        return round(
            numero,
            2,
        )

    @staticmethod
    def _preco(
        valor,
    ) -> float | None:
        if valor is None:
            return None

        try:
            numero = float(valor)

        except (
            TypeError,
            ValueError,
        ):
            return None

        if numero <= 0:
            return None

        return round(
            numero,
            2,
        )

    @staticmethod
    def _dinheiro_br(
        valor: str,
    ) -> float | None:
        bruto = re.sub(
            r"\s+",
            "",
            str(valor or ""),
        )

        if not bruto:
            return None

        # 3.470,50 -> 3470.50
        if "," in bruto:
            bruto = bruto.replace(
                ".",
                "",
            ).replace(
                ",",
                ".",
            )

        else:
            # 3.470 -> 3470
            partes = bruto.split(".")

            if len(partes) > 1 and all(len(parte) == 3 for parte in partes[1:]):
                bruto = "".join(partes)

        try:
            numero = float(bruto)

        except ValueError:
            return None

        if numero <= 0:
            return None

        return round(
            numero,
            2,
        )

    @staticmethod
    def _precos_conferem(
        primeiro: float,
        segundo: float,
    ) -> bool:
        # Permite arredondamento de mensagem social,
        # mas nao grandes diferencas promocionais.
        tolerancia = max(
            1.0,
            min(
                primeiro,
                segundo,
            )
            * 0.002,
        )

        return abs(primeiro - segundo) <= tolerancia
