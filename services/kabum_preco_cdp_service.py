# 63.8738, -149.7525

from __future__ import annotations

import json
import logging
import math
import re
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ResultadoPrecoKabum:
    produto_id: str
    valido: bool
    motivo: str

    url_produto: str | None = None
    titulo: str = ""
    preco_brl: float | None = None
    disponivel: bool | None = None


class KabumPrecoCdpService:
    URL_CANONICA = "https://www.kabum.com.br/" "produto/{produto_id}"

    PADRAO_PRODUTO = re.compile(
        r"/produto/(\d+)(?:/|$)",
        flags=re.IGNORECASE,
    )

    MOTIVO_DESAFIO = "erro_kabum_desafio_humano"

    MOTIVO_COOLDOWN = "erro_kabum_cooldown_desafio"

    ARQUIVO_COOLDOWN_PADRAO = Path.home() / ".radar_de_ofertas" / "kabum_cooldown.txt"

    MARCADORES_DESAFIO = (
        "verify you are human",
        "verifique se voce e humano",
        "verifique se voc? ? humano",
        "captcha",
        "cf-chl-",
        "access denied",
    )

    def __init__(
        self,
        endpoint_cdp: str = ("http://127.0.0.1:9222"),
        timeout_navegacao_ms: int = 90_000,
        espera_pos_carga_ms: int = 2_000,
        cooldown_desafio_segundos: int = 1_800,
        arquivo_cooldown: str | Path | None = ARQUIVO_COOLDOWN_PADRAO,
    ) -> None:
        endpoint_cdp = str(endpoint_cdp).strip()

        if not endpoint_cdp:
            raise ValueError("endpoint_cdp nao pode ser vazio.")

        if timeout_navegacao_ms <= 0:
            raise ValueError("timeout_navegacao_ms precisa " "ser maior que zero.")

        if espera_pos_carga_ms < 0:
            raise ValueError("espera_pos_carga_ms nao pode " "ser negativa.")

        if cooldown_desafio_segundos < 0:
            raise ValueError("cooldown_desafio_segundos " "nao pode ser negativo.")

        self.endpoint_cdp = endpoint_cdp

        self.timeout_navegacao_ms = timeout_navegacao_ms

        self.espera_pos_carga_ms = espera_pos_carga_ms

        self.cooldown_desafio_segundos = cooldown_desafio_segundos

        self.arquivo_cooldown = (
            Path(arquivo_cooldown).expanduser() if arquivo_cooldown is not None else None
        )

        self._desafio_ate_monotonic = 0.0

    def validar(
        self,
        produto_id: str,
        url_produto: str | None = None,
    ) -> ResultadoPrecoKabum:
        produto_id = str(produto_id or "").strip()

        if not produto_id.isdigit():
            return self._rejeitar(
                produto_id,
                "id_produto_kabum_invalido",
            )

        url = str(url_produto or self.URL_CANONICA.format(produto_id=produto_id)).strip()

        if self._em_cooldown_desafio():
            logger.warning(
                "KaBuM em cooldown apos " "verificacao humana. " "Validacao CDP ignorada."
            )

            return self._rejeitar(
                produto_id,
                self.MOTIVO_COOLDOWN,
                url_produto=url,
            )

        pagina = None
        contexto_criado = None

        try:
            with sync_playwright() as playwright:
                navegador = playwright.chromium.connect_over_cdp(self.endpoint_cdp)

                if navegador.contexts:
                    contexto = navegador.contexts[0]

                else:
                    contexto = navegador.new_context()

                    contexto_criado = contexto

                pagina = contexto.new_page()

                pagina.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=(self.timeout_navegacao_ms),
                )

                pagina.wait_for_timeout(self.espera_pos_carga_ms)

                url_final = str(pagina.url or "")

                html = pagina.content()

                if self._pagina_desafio(html):
                    self._ativar_cooldown_desafio()

                    return self._rejeitar(
                        produto_id,
                        self.MOTIVO_DESAFIO,
                        url_produto=url_final,
                    )

                scripts = pagina.locator(
                    "script[" 'type="application/ld+json"' "]"
                ).all_text_contents()

                return self.analisar_jsonld(
                    produto_id=produto_id,
                    url_final=url_final,
                    scripts=scripts,
                )

        except Exception as erro:
            return self._rejeitar(
                produto_id,
                ("erro_kabum_pdp:" f"{type(erro).__name__}"),
                url_produto=url,
            )

        finally:
            if pagina is not None:
                try:
                    pagina.close()

                except Exception:
                    pass

            if contexto_criado is not None:
                try:
                    contexto_criado.close()

                except Exception:
                    pass

    @classmethod
    def analisar_jsonld(
        cls,
        *,
        produto_id: str,
        url_final: str,
        scripts: list[str] | tuple[str, ...],
    ) -> ResultadoPrecoKabum:
        final_id = cls._produto_id_url(url_final)

        if final_id != produto_id:
            return cls._rejeitar(
                produto_id,
                "produto_kabum_redirecionado",
                url_produto=url_final,
            )

        produtos = []

        for bruto in scripts:
            try:
                dados = json.loads(bruto)

            except Exception:
                continue

            for item in cls._percorrer_json(dados):
                tipo = item.get("@type")

                tipos = (
                    tipo
                    if isinstance(
                        tipo,
                        list,
                    )
                    else [
                        tipo,
                    ]
                )

                if "Product" in tipos:
                    produtos.append(item)

        if not produtos:
            return cls._rejeitar(
                produto_id,
                ("erro_kabum_" "jsonld_product_ausente"),
                url_produto=url_final,
            )

        titulo = ""
        precos = set()
        disponibilidades = []

        for produto in produtos:
            nome = str(produto.get("name") or "").strip()

            if nome and not titulo:
                titulo = nome

            offers = produto.get("offers")

            if isinstance(
                offers,
                dict,
            ):
                offers = [
                    offers,
                ]

            if not isinstance(
                offers,
                list,
            ):
                continue

            for offer in offers:
                if not isinstance(
                    offer,
                    dict,
                ):
                    continue

                moeda = str(offer.get("priceCurrency") or "").upper()

                if moeda == "BRL":
                    preco = cls._numero(offer.get("price"))

                    if preco is not None:
                        precos.add(preco)

                disponibilidade = str(offer.get("availability") or "").strip()

                if disponibilidade:
                    disponibilidades.append(disponibilidade.casefold())

        if not precos:
            return cls._rejeitar(
                produto_id,
                "preco_kabum_brl_ausente",
                url_produto=url_final,
            )

        if len(precos) != 1:
            return cls._rejeitar(
                produto_id,
                "precos_kabum_ambiguos",
                url_produto=url_final,
            )

        tem_estoque = any(valor.endswith("/instock") for valor in disponibilidades)

        sem_estoque = any(valor.endswith("/outofstock") for valor in disponibilidades)

        disponivel = None

        if tem_estoque and not sem_estoque:
            disponivel = True

        elif sem_estoque and not tem_estoque:
            disponivel = False

        return ResultadoPrecoKabum(
            produto_id=produto_id,
            valido=True,
            motivo=("preco_kabum_" "confirmado_jsonld"),
            url_produto=cls._limpar_url(url_final),
            titulo=titulo,
            preco_brl=next(iter(precos)),
            disponivel=disponivel,
        )

    def _ativar_cooldown_desafio(
        self,
    ) -> None:
        duracao = float(self.cooldown_desafio_segundos)

        self._desafio_ate_monotonic = time.monotonic() + duracao

        if self.arquivo_cooldown is None:
            return

        if duracao <= 0:
            self._limpar_cooldown_persistente()
            return

        expira_em_epoch = time.time() + duracao

        try:
            self.arquivo_cooldown.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            temporario = self.arquivo_cooldown.with_name(self.arquivo_cooldown.name + ".tmp")

            temporario.write_text(
                f"{expira_em_epoch:.6f}",
                encoding="utf-8",
            )

            temporario.replace(self.arquivo_cooldown)

        except OSError:
            logger.exception("Nao foi possivel persistir " "o cooldown da KaBuM.")

    def _em_cooldown_desafio(
        self,
    ) -> bool:
        agora_monotonic = time.monotonic()

        if agora_monotonic < self._desafio_ate_monotonic:
            return True

        if self.arquivo_cooldown is None:
            return False

        try:
            if not self.arquivo_cooldown.is_file():
                return False

            texto = self.arquivo_cooldown.read_text(encoding="utf-8").strip()

            expira_em_epoch = float(texto)

            if not math.isfinite(expira_em_epoch):
                raise ValueError("timestamp de cooldown " "nao finito")

        except (
            OSError,
            ValueError,
        ):
            logger.warning(
                "Estado de cooldown da KaBuM " "invalido. O arquivo sera " "descartado.",
                exc_info=True,
            )

            self._limpar_cooldown_persistente()

            return False

        restante = expira_em_epoch - time.time()

        if restante <= 0:
            self._limpar_cooldown_persistente()
            return False

        self._desafio_ate_monotonic = agora_monotonic + restante

        return True

    def _limpar_cooldown_persistente(
        self,
    ) -> None:
        if self.arquivo_cooldown is None:
            return

        try:
            self.arquivo_cooldown.unlink(missing_ok=True)

        except OSError:
            logger.exception("Nao foi possivel remover " "o cooldown persistente " "da KaBuM.")

    @classmethod
    def _pagina_desafio(
        cls,
        html: str,
    ) -> bool:
        texto = str(html or "").casefold()

        return any(marcador in texto for marcador in cls.MARCADORES_DESAFIO)

    @classmethod
    def _produto_id_url(
        cls,
        url: str,
    ) -> str | None:
        try:
            partes = urlsplit(str(url or ""))

        except ValueError:
            return None

        host = (partes.hostname or "").casefold()

        if host not in {
            "kabum.com.br",
            "www.kabum.com.br",
        }:
            return None

        match = cls.PADRAO_PRODUTO.search(partes.path)

        if not match:
            return None

        return match.group(1)

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
    def _limpar_url(
        url: str,
    ) -> str:
        try:
            partes = urlsplit(str(url or ""))

        except ValueError:
            return ""

        return f"{partes.scheme}://" f"{partes.netloc}" f"{partes.path}"

    @classmethod
    def _percorrer_json(
        cls,
        valor,
    ):
        if isinstance(
            valor,
            dict,
        ):
            yield valor

            for filho in valor.values():
                yield from cls._percorrer_json(filho)

        elif isinstance(
            valor,
            list,
        ):
            for filho in valor:
                yield from cls._percorrer_json(filho)

    @staticmethod
    def _rejeitar(
        produto_id: str,
        motivo: str,
        *,
        url_produto: str | None = None,
    ) -> ResultadoPrecoKabum:
        return ResultadoPrecoKabum(
            produto_id=str(produto_id or ""),
            valido=False,
            motivo=motivo,
            url_produto=url_produto,
        )
