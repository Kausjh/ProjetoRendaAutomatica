# 63.8738, -149.7525

from __future__ import annotations

import re

from models.plano_discovery_scout import (
    PlanoDiscoveryScout,
)
from models.resolucao_scout import ResolucaoScout
from models.sinal_scout import SinalScout


class PlanejadorDiscoveryScout:
    """Transforma landing pages resolvidas em planos conservadores de discovery."""

    ESTRATEGIA_KABUM_TERMOS = "buscar_termos_kabum"

    ESTRATEGIA_KABUM_LANDING = "explorar_landing_kabum"

    ESTRATEGIA_ALIEXPRESS_FEED = "feed_curado_aliexpress"

    ESTRATEGIA_IGNORAR = "ignorar"

    GENERICOS_KABUM = {
        "item",
        "itens",
        "produto",
        "produtos",
        "selecionado",
        "selecionados",
        "selecionada",
        "selecionadas",
        "promocao",
        "promo??o",
        "oferta",
        "ofertas",
    }

    PADROES_KABUM = (
        re.compile(
            r"\blinha\s+" r"([A-Za-z0-9][A-Za-z0-9._-]{2,})",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bprodutos?\s+" r"(?:da|do|de)\s+" r"([A-Za-z0-9][A-Za-z0-9._-]{2,})",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bprodutos?\s+" r"([A-Za-z0-9][A-Za-z0-9._-]{2,})",
            re.IGNORECASE,
        ),
    )

    PADRAO_MESA_DIGITALIZADORA = re.compile(
        r"\bmesas?\s+digitalizadoras?\b",
        re.IGNORECASE,
    )

    def planejar(
        self,
        sinal: SinalScout,
        resolucao: ResolucaoScout,
    ) -> PlanoDiscoveryScout:
        if resolucao.status != "landing_page":
            return self._ignorar(
                sinal=sinal,
                resolucao=resolucao,
                motivo=("resolucao_nao_e_landing_page"),
            )

        marketplace = str(resolucao.marketplace or "").strip().casefold()

        if marketplace == "aliexpress":
            return self._planejar_aliexpress(
                sinal=sinal,
                resolucao=resolucao,
            )

        if marketplace == "kabum":
            return self._planejar_kabum(
                sinal=sinal,
                resolucao=resolucao,
            )

        return self._ignorar(
            sinal=sinal,
            resolucao=resolucao,
            motivo=("marketplace_sem_discovery"),
        )

    def _planejar_aliexpress(
        self,
        sinal: SinalScout,
        resolucao: ResolucaoScout,
    ) -> PlanoDiscoveryScout:
        texto = self._texto_sinal(sinal)

        if "chile" in texto.casefold():
            return self._ignorar(
                sinal=sinal,
                resolucao=resolucao,
                motivo=("campanha_regional_fora_br"),
            )

        return PlanoDiscoveryScout(
            fonte=sinal.fonte,
            id_externo=sinal.id_externo,
            marketplace="aliexpress",
            estrategia=(self.ESTRATEGIA_ALIEXPRESS_FEED),
            termos_busca=(),
            utilizavel=True,
            motivo=("campanha_geral_marketplace"),
        )

    def _planejar_kabum(
        self,
        sinal: SinalScout,
        resolucao: ResolucaoScout,
    ) -> PlanoDiscoveryScout:
        texto = self._texto_sinal(sinal)

        termos = self._extrair_termos_kabum(texto)

        if termos:
            return PlanoDiscoveryScout(
                fonte=sinal.fonte,
                id_externo=sinal.id_externo,
                marketplace="kabum",
                estrategia=(self.ESTRATEGIA_KABUM_TERMOS),
                termos_busca=termos,
                utilizavel=True,
                motivo=("campanha_com_termo_especifico"),
            )

        return PlanoDiscoveryScout(
            fonte=sinal.fonte,
            id_externo=sinal.id_externo,
            marketplace="kabum",
            estrategia=(self.ESTRATEGIA_KABUM_LANDING),
            termos_busca=(),
            utilizavel=True,
            motivo=("campanha_sem_termo_confiavel"),
        )

    @classmethod
    def _extrair_termos_kabum(
        cls,
        texto: str,
    ) -> tuple[str, ...]:
        termos: list[str] = []

        mesa = cls.PADRAO_MESA_DIGITALIZADORA.search(texto)

        if mesa is not None:
            termos.append(mesa.group(0).strip())

        for padrao in cls.PADROES_KABUM:
            correspondencia = padrao.search(texto)

            if correspondencia is None:
                continue

            candidato = correspondencia.group(1).strip()

            candidato = candidato.rstrip(".,;:!?")

            if candidato.casefold() in cls.GENERICOS_KABUM:
                continue

            termos.append(candidato)

        resultado: list[str] = []
        vistos: set[str] = set()

        for termo in termos:
            chave = termo.casefold()

            if chave in vistos:
                continue

            vistos.add(chave)
            resultado.append(termo)

        return tuple(resultado)

    @staticmethod
    def _texto_sinal(
        sinal: SinalScout,
    ) -> str:
        partes = (
            sinal.titulo,
            sinal.descricao,
            sinal.termos,
        )

        return " ".join(str(parte or "").strip() for parte in partes if str(parte or "").strip())

    def _ignorar(
        self,
        sinal: SinalScout,
        resolucao: ResolucaoScout,
        motivo: str,
    ) -> PlanoDiscoveryScout:
        return PlanoDiscoveryScout(
            fonte=sinal.fonte,
            id_externo=sinal.id_externo,
            marketplace=(resolucao.marketplace),
            estrategia=(self.ESTRATEGIA_IGNORAR),
            termos_busca=(),
            utilizavel=False,
            motivo=motivo,
        )
