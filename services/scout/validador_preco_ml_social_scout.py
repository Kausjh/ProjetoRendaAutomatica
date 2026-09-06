# 63.8738, -149.7525

from __future__ import annotations

from typing import Any

from playwright.sync_api import (
    Error as PlaywrightError,
)
from playwright.sync_api import (
    sync_playwright,
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


class ValidadorPrecoMercadoLivreSocialScout:
    """
    Valida o preco descoberto pelo Social Scout diretamente
    na pagina oficial do Mercado Livre.

    O preco do grupo nunca e tratado como fonte de verdade.

    A validacao separa:
    - preco anterior;
    - preco atual;
    - preco Pix;
    - total parcelado;
    - valor da parcela;
    - cupom informado pela fonte.

    Cupom nao e considerado validado apenas porque o calculo
    informado pelo grupo e matematicamente coerente.
    """

    MARKETPLACE = "mercado_livre"

    STATUS_VALIDADO = "validado"
    STATUS_DIVERGENTE = "divergente"
    STATUS_INDISPONIVEL = "indisponivel"
    STATUS_NAO_SUPORTADO = "nao_suportado"
    STATUS_ERRO = "erro"

    def __init__(
        self,
        endpoint_cdp: str = "http://127.0.0.1:9222",
        tolerancia_preco: float = 0.02,
    ) -> None:
        self.endpoint_cdp = str(endpoint_cdp).strip() or "http://127.0.0.1:9222"

        self.tolerancia_preco = max(
            float(tolerancia_preco),
            0.0,
        )

    def validar(
        self,
        deteccao: ResultadoDeteccaoSocialScout,
        resolucao: ResultadoResolucaoSocialScout,
    ) -> ResultadoValidacaoPrecoSocialScout:
        if (
            resolucao.status != "resolvido"
            or resolucao.marketplace != self.MARKETPLACE
            or not resolucao.url_destino
        ):
            return ResultadoValidacaoPrecoSocialScout(
                status=self.STATUS_NAO_SUPORTADO,
                marketplace=resolucao.marketplace,
                url=resolucao.url_destino,
                preco_original_grupo=deteccao.preco_original,
                preco_oferta_grupo=deteccao.preco_oferta,
                preco_final_grupo=deteccao.preco_final,
                codigo_cupom=deteccao.codigo_cupom,
                desconto_cupom_percentual=(deteccao.desconto_cupom_percentual),
                motivo=("resolucao_social_nao_e_produto_" "mercado_livre_resolvido"),
            )

        try:
            snapshot = self._capturar_snapshot(resolucao.url_destino)

        except Exception as erro:
            return ResultadoValidacaoPrecoSocialScout(
                status=self.STATUS_ERRO,
                marketplace=self.MARKETPLACE,
                url=resolucao.url_destino,
                preco_original_grupo=deteccao.preco_original,
                preco_oferta_grupo=deteccao.preco_oferta,
                preco_final_grupo=deteccao.preco_final,
                codigo_cupom=deteccao.codigo_cupom,
                desconto_cupom_percentual=(deteccao.desconto_cupom_percentual),
                motivo=("falha_ao_consultar_preco_oficial:" f"{type(erro).__name__}"),
            )

        return self._avaliar_snapshot(
            deteccao=deteccao,
            resolucao=resolucao,
            snapshot=snapshot,
        )

    def _avaliar_snapshot(
        self,
        *,
        deteccao: ResultadoDeteccaoSocialScout,
        resolucao: ResultadoResolucaoSocialScout,
        snapshot: dict[str, Any],
    ) -> ResultadoValidacaoPrecoSocialScout:
        preco_oficial = self._numero(snapshot.get("preco_oficial"))

        preco_original = self._numero(snapshot.get("preco_original"))

        preco_parcelado = self._numero(snapshot.get("preco_parcelado"))

        valor_parcela = self._numero(snapshot.get("valor_parcela"))

        parcelas = self._inteiro(snapshot.get("parcelas"))

        disponivel = snapshot.get("disponivel")

        if not isinstance(
            disponivel,
            bool,
        ):
            disponivel = None

        titulo_oficial = str(
            snapshot.get(
                "titulo",
                "",
            )
            or ""
        ).strip()

        tipo_preco = (
            str(
                snapshot.get(
                    "tipo_preco",
                    "",
                )
                or ""
            ).strip()
            or None
        )

        preco_valido_ate = (
            str(
                snapshot.get(
                    "preco_valido_ate",
                    "",
                )
                or ""
            ).strip()
            or None
        )

        if preco_oficial is None:
            return self._resultado(
                status=self.STATUS_ERRO,
                deteccao=deteccao,
                resolucao=resolucao,
                titulo_oficial=titulo_oficial,
                preco_oficial=None,
                preco_original=preco_original,
                tipo_preco=tipo_preco,
                preco_parcelado=preco_parcelado,
                parcelas=parcelas,
                valor_parcela=valor_parcela,
                disponivel=disponivel,
                preco_valido_ate=preco_valido_ate,
                preco_base_confere=False,
                preco_original_confere=None,
                preco_final_coerente=None,
                motivo="preco_oficial_nao_encontrado",
            )

        if disponivel is False:
            return self._resultado(
                status=self.STATUS_INDISPONIVEL,
                deteccao=deteccao,
                resolucao=resolucao,
                titulo_oficial=titulo_oficial,
                preco_oficial=preco_oficial,
                preco_original=preco_original,
                tipo_preco=tipo_preco,
                preco_parcelado=preco_parcelado,
                parcelas=parcelas,
                valor_parcela=valor_parcela,
                disponivel=False,
                preco_valido_ate=preco_valido_ate,
                preco_base_confere=False,
                preco_original_confere=None,
                preco_final_coerente=None,
                motivo="produto_oficial_indisponivel",
            )

        preco_grupo = deteccao.preco_oferta

        if preco_grupo is None:
            return self._resultado(
                status=self.STATUS_ERRO,
                deteccao=deteccao,
                resolucao=resolucao,
                titulo_oficial=titulo_oficial,
                preco_oficial=preco_oficial,
                preco_original=preco_original,
                tipo_preco=tipo_preco,
                preco_parcelado=preco_parcelado,
                parcelas=parcelas,
                valor_parcela=valor_parcela,
                disponivel=disponivel,
                preco_valido_ate=preco_valido_ate,
                preco_base_confere=False,
                preco_original_confere=None,
                preco_final_coerente=None,
                motivo="mensagem_social_sem_preco_base",
            )

        preco_base_confere = self._iguais(
            preco_oficial,
            preco_grupo,
        )

        preco_original_confere: bool | None = None

        if deteccao.preco_original is not None and preco_original is not None:
            preco_original_confere = self._iguais(
                preco_original,
                deteccao.preco_original,
            )

        preco_final_coerente = self._validar_calculo_cupom(
            preco_base=preco_oficial,
            preco_final=deteccao.preco_final,
            percentual=deteccao.desconto_cupom_percentual,
            codigo=deteccao.codigo_cupom,
        )

        divergencia = not preco_base_confere

        if preco_original_confere is False:
            divergencia = True

        if preco_final_coerente is False:
            divergencia = True

        if divergencia:
            return self._resultado(
                status=self.STATUS_DIVERGENTE,
                deteccao=deteccao,
                resolucao=resolucao,
                titulo_oficial=titulo_oficial,
                preco_oficial=preco_oficial,
                preco_original=preco_original,
                tipo_preco=tipo_preco,
                preco_parcelado=preco_parcelado,
                parcelas=parcelas,
                valor_parcela=valor_parcela,
                disponivel=disponivel,
                preco_valido_ate=preco_valido_ate,
                preco_base_confere=preco_base_confere,
                preco_original_confere=(preco_original_confere),
                preco_final_coerente=(preco_final_coerente),
                motivo=("precos_da_fonte_divergem_" "dos_dados_oficiais"),
            )

        motivo = "preco_oficial_confere"

        if deteccao.codigo_cupom:
            motivo = "preco_base_oficial_confere_" "cupom_ainda_nao_validado"

        return self._resultado(
            status=self.STATUS_VALIDADO,
            deteccao=deteccao,
            resolucao=resolucao,
            titulo_oficial=titulo_oficial,
            preco_oficial=preco_oficial,
            preco_original=preco_original,
            tipo_preco=tipo_preco,
            preco_parcelado=preco_parcelado,
            parcelas=parcelas,
            valor_parcela=valor_parcela,
            disponivel=disponivel,
            preco_valido_ate=preco_valido_ate,
            preco_base_confere=True,
            preco_original_confere=(preco_original_confere),
            preco_final_coerente=(preco_final_coerente),
            motivo=motivo,
        )

    def _capturar_snapshot(
        self,
        url: str,
    ) -> dict[str, Any]:
        with sync_playwright() as playwright:
            navegador = playwright.chromium.connect_over_cdp(
                self.endpoint_cdp,
                timeout=10000,
            )

            if not navegador.contexts:
                raise RuntimeError("Chrome CDP sem contexto disponivel.")

            contexto = navegador.contexts[0]

            pagina = contexto.new_page()

            pagina.set_default_timeout(10000)

            try:
                pagina.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=45000,
                )

                pagina.wait_for_timeout(3000)

                return pagina.evaluate(r"""
                    () => {
                        const texto = (el) => (
                            el && el.textContent
                                ? el.textContent
                                    .replace(/\s+/g, " ")
                                    .trim()
                                : ""
                        );

                        const money = (el) => {
                            if (!el) {
                                return null;
                            }

                            const fraction = el.querySelector(
                                "[data-andes-money-amount-fraction='true']"
                            );

                            if (!fraction) {
                                return null;
                            }

                            const inteiro = texto(fraction)
                                .replace(/\D/g, "");

                            if (!inteiro) {
                                return null;
                            }

                            const cents = el.querySelector(
                                "[data-andes-money-amount-cents='true']"
                            );

                            const centavos = cents
                                ? texto(cents).replace(/\D/g, "")
                                : "";

                            let valor = Number(inteiro);

                            if (
                                centavos
                                && !Number.isNaN(
                                    Number(centavos)
                                )
                            ) {
                                valor += (
                                    Number(
                                        centavos
                                            .padEnd(2, "0")
                                            .slice(0, 2)
                                    )
                                    / 100
                                );
                            }

                            return Number(
                                valor.toFixed(2)
                            );
                        };

                        const numero = (valor) => {
                            const convertido = Number(valor);

                            return Number.isFinite(convertido)
                                ? convertido
                                : null;
                        };

                        let jsonPrice = null;
                        let jsonTitle = "";
                        let availability = null;
                        let priceValidUntil = null;

                        const visitar = (item) => {
                            if (
                                item === null
                                || item === undefined
                            ) {
                                return;
                            }

                            if (Array.isArray(item)) {
                                item.forEach(visitar);
                                return;
                            }

                            if (typeof item !== "object") {
                                return;
                            }

                            const tipo = item["@type"];

                            const ehProduto = (
                                tipo === "Product"
                                || (
                                    Array.isArray(tipo)
                                    && tipo.includes("Product")
                                )
                            );

                            if (ehProduto) {
                                if (
                                    !jsonTitle
                                    && typeof item.name === "string"
                                ) {
                                    jsonTitle = item.name.trim();
                                }

                                let oferta = item.offers;

                                if (Array.isArray(oferta)) {
                                    oferta = oferta[0];
                                }

                                if (
                                    oferta
                                    && typeof oferta === "object"
                                ) {
                                    if (jsonPrice === null) {
                                        jsonPrice = numero(
                                            oferta.price
                                        );
                                    }

                                    if (
                                        typeof oferta.availability
                                        === "string"
                                    ) {
                                        const dispon = (
                                            oferta.availability
                                            .toLowerCase()
                                        );

                                        if (
                                            dispon.includes(
                                                "instock"
                                            )
                                        ) {
                                            availability = true;
                                        }
                                        else if (
                                            dispon.includes(
                                                "outofstock"
                                            )
                                        ) {
                                            availability = false;
                                        }
                                    }

                                    if (
                                        oferta.priceValidUntil
                                        !== undefined
                                        && oferta.priceValidUntil
                                        !== null
                                    ) {
                                        priceValidUntil = String(
                                            oferta.priceValidUntil
                                        );
                                    }
                                }
                            }

                            if (item["@graph"]) {
                                visitar(item["@graph"]);
                            }
                        };

                        document
                            .querySelectorAll(
                                "script[type='application/ld+json']"
                            )
                            .forEach((script) => {
                                try {
                                    visitar(
                                        JSON.parse(
                                            script.textContent
                                            || ""
                                        )
                                    );
                                }
                                catch (_) {
                                    // JSON-LD invalido e ignorado.
                                }
                            });

                        const itempropPrice = numero(
                            document.querySelector(
                                "meta[itemprop='price']"
                            )?.content
                        );

                        const atualEl = document.querySelector(
                            ".ui-pdp-price__second-line "
                            + ".andes-money-amount"
                        );

                        const anteriorEl = document.querySelector(
                            ".ui-pdp-price__original-value"
                        );

                        const blocoAtual = document.querySelector(
                            ".ui-pdp-price__second-line"
                        );

                        const textoAtual = texto(
                            blocoAtual
                        ).toLowerCase();

                        const precoDom = money(
                            atualEl
                        );

                        const precoOficial = (
                            itempropPrice
                            ?? jsonPrice
                            ?? precoDom
                        );

                        let tipoPreco = "atual";

                        const mainContainer = document.querySelector(
                            ".ui-pdp-price__main-container"
                        );

                        const mainText = texto(
                            mainContainer
                        ).toLowerCase();

                        if (
                            textoAtual.includes("pix")
                            || mainText.includes(
                                "no pix"
                            )
                        ) {
                            tipoPreco = "pix";
                        }

                        const subtitles = document.querySelector(
                            ".ui-pdp-price__subtitles"
                        );

                        const installmentAmounts = subtitles
                            ? Array.from(
                                subtitles.querySelectorAll(
                                    ".andes-money-amount"
                                )
                            ).map(money).filter(
                                (valor) => valor !== null
                            )
                            : [];

                        const installmentText = texto(
                            subtitles
                        );

                        const matchParcelas = (
                            installmentText.match(
                                /em\s+(\d+)x/i
                            )
                        );

                        const h1 = texto(
                            document.querySelector("h1")
                        );

                        return {
                            titulo: (
                                jsonTitle
                                || h1
                                || document.title
                                || ""
                            ),

                            preco_oficial: precoOficial,

                            preco_original: money(
                                anteriorEl
                            ),

                            tipo_preco: tipoPreco,

                            preco_parcelado: (
                                installmentAmounts.length >= 1
                                    ? installmentAmounts[0]
                                    : null
                            ),

                            valor_parcela: (
                                installmentAmounts.length >= 2
                                    ? installmentAmounts[1]
                                    : null
                            ),

                            parcelas: (
                                matchParcelas
                                    ? Number(matchParcelas[1])
                                    : null
                            ),

                            disponivel: availability,

                            preco_valido_ate: (
                                priceValidUntil
                            ),
                        };
                    }
                    """)

            except PlaywrightError:
                raise

            finally:
                if not pagina.is_closed():
                    pagina.close()

                # Nao chamamos browser.close().
                # O Chrome CDP e compartilhado pelo projeto.

    def _validar_calculo_cupom(
        self,
        *,
        preco_base: float,
        preco_final: float | None,
        percentual: float | None,
        codigo: str | None,
    ) -> bool | None:
        if not codigo:
            return None

        if preco_final is None or percentual is None:
            return None

        esperado = round(
            preco_base * (1.0 - (percentual / 100.0)),
            2,
        )

        return self._iguais(
            esperado,
            preco_final,
        )

    def _iguais(
        self,
        primeiro: float,
        segundo: float,
    ) -> bool:
        return abs(float(primeiro) - float(segundo)) <= self.tolerancia_preco

    @staticmethod
    def _numero(
        valor: object,
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
    def _inteiro(
        valor: object,
    ) -> int | None:
        if valor is None:
            return None

        try:
            numero = int(valor)

        except (
            TypeError,
            ValueError,
        ):
            return None

        if numero <= 0:
            return None

        return numero

    def _resultado(
        self,
        *,
        status: str,
        deteccao: ResultadoDeteccaoSocialScout,
        resolucao: ResultadoResolucaoSocialScout,
        titulo_oficial: str,
        preco_oficial: float | None,
        preco_original: float | None,
        tipo_preco: str | None,
        preco_parcelado: float | None,
        parcelas: int | None,
        valor_parcela: float | None,
        disponivel: bool | None,
        preco_valido_ate: str | None,
        preco_base_confere: bool,
        preco_original_confere: bool | None,
        preco_final_coerente: bool | None,
        motivo: str,
    ) -> ResultadoValidacaoPrecoSocialScout:
        return ResultadoValidacaoPrecoSocialScout(
            status=status,
            marketplace=self.MARKETPLACE,
            url=resolucao.url_destino,
            titulo_oficial=titulo_oficial,
            preco_oficial=preco_oficial,
            preco_original_oficial=preco_original,
            tipo_preco_oficial=tipo_preco,
            preco_parcelado_oficial=preco_parcelado,
            parcelas=parcelas,
            valor_parcela=valor_parcela,
            disponivel=disponivel,
            preco_valido_ate=preco_valido_ate,
            preco_original_grupo=deteccao.preco_original,
            preco_oferta_grupo=deteccao.preco_oferta,
            preco_final_grupo=deteccao.preco_final,
            codigo_cupom=deteccao.codigo_cupom,
            desconto_cupom_percentual=(deteccao.desconto_cupom_percentual),
            preco_base_confere=preco_base_confere,
            preco_original_confere=(preco_original_confere),
            preco_final_coerente_com_desconto=(preco_final_coerente),
            cupom_validado=False,
            motivo=motivo,
        )
