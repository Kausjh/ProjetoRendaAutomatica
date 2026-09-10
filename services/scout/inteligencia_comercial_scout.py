# 63.8738, -149.7525

from __future__ import annotations

from models.perfil_comercial_scout import (
    PerfilComercialScout,
)
from models.plano_discovery_scout import (
    PlanoDiscoveryScout,
)
from models.resolucao_scout import ResolucaoScout
from models.sinal_scout import SinalScout


class InteligenciaComercialScout:
    """
    Estrutura sinais comerciais sem transformar observacao
    em verdade oficial.

    Responsabilidades desta V1:
    - reconhecer campanha;
    - reconhecer voucher/cupom explicitamente informado;
    - preservar parceiro/advertiser;
    - organizar janela temporal e regioes;
    - carregar estrategia de discovery decidida pelo planejador.

    Nao e responsabilidade desta classe:
    - validar aplicabilidade de cupom;
    - definir preco efetivo;
    - identificar seller do marketplace;
    - declarar tendencia a partir de um unico sinal;
    - alterar score, historico ou publicacao.
    """

    _MARCADORES_CAMPANHA = (
        "promotion",
        "promo",
        "campaign",
        "campanha",
        "voucher",
        "offer",
        "oferta",
    )

    def analisar(
        self,
        sinal: SinalScout,
        resolucao: ResolucaoScout | None = None,
        plano: PlanoDiscoveryScout | None = None,
    ) -> PerfilComercialScout:
        self._validar_identidade(
            sinal=sinal,
            resolucao=resolucao,
            plano=plano,
        )

        tipo_sinal = str(sinal.tipo or "").strip().casefold() or "desconhecido"

        titulo = str(sinal.titulo or "").strip()

        marketplace = self._obter_marketplace(
            resolucao=resolucao,
            plano=plano,
        )

        tipo_destino = None

        if resolucao is not None:
            tipo_destino = str(resolucao.tipo_destino or "").strip() or None

        parceiro_id = str(sinal.advertiser_id or "").strip() or None

        parceiro_nome = str(sinal.advertiser_nome or "").strip() or None

        codigo_voucher = str(sinal.codigo_voucher or "").strip() or None

        inicio = str(sinal.inicio or "").strip() or None

        fim = str(sinal.fim or "").strip() or None

        regioes = self._normalizar_regioes(sinal.regioes)

        estrategia_discovery = None
        termos_descoberta: tuple[str, ...] = ()
        utilizavel_discovery = False

        if plano is not None:
            estrategia_discovery = str(plano.estrategia or "").strip() or None

            termos_descoberta = self._normalizar_termos(plano.termos_busca)

            utilizavel_discovery = bool(
                plano.utilizavel and estrategia_discovery and estrategia_discovery != "ignorar"
            )

        landing_page = bool(
            resolucao is not None
            and str(resolucao.status or "").strip().casefold() == "landing_page"
        )

        dimensoes: list[str] = []
        evidencias: list[str] = []

        if self._eh_campanha(tipo_sinal):
            dimensoes.append("campanha")

            evidencias.append("tipo_comercial")

        if codigo_voucher is not None:
            dimensoes.append("cupom")

            evidencias.append("voucher_explicito")

        if parceiro_id is not None or parceiro_nome is not None:
            dimensoes.append("parceiro")

            evidencias.append("advertiser_identificado")

        if termos_descoberta:
            dimensoes.append("termos_discovery")

            evidencias.append("termos_curados_pelo_planejador")

        if inicio is not None or fim is not None:
            dimensoes.append("janela_temporal")

            evidencias.append("janela_temporal_explicita")

        if regioes:
            dimensoes.append("regional")

            evidencias.append("regioes_explicitas")

        if landing_page:
            dimensoes.append("landing_page")

            evidencias.append("destino_resolvido_como_landing")

        if utilizavel_discovery:
            evidencias.append("rota_discovery_utilizavel")

        return PerfilComercialScout(
            fonte=str(sinal.fonte or "").strip(),
            id_externo=str(sinal.id_externo or "").strip(),
            tipo_sinal=tipo_sinal,
            titulo=titulo,
            marketplace=marketplace,
            tipo_destino=tipo_destino,
            parceiro_id=parceiro_id,
            parceiro_nome=parceiro_nome,
            codigo_voucher=codigo_voucher,
            inicio=inicio,
            fim=fim,
            regioes=regioes,
            estrategia_discovery=estrategia_discovery,
            termos_descoberta=termos_descoberta,
            dimensoes=tuple(dimensoes),
            evidencias=tuple(evidencias),
            landing_page=landing_page,
            utilizavel_discovery=utilizavel_discovery,
        )

    @classmethod
    def _eh_campanha(
        cls,
        tipo_sinal: str,
    ) -> bool:
        normalizado = tipo_sinal.replace(
            "-",
            "_",
        ).replace(
            " ",
            "_",
        )

        return any(marcador in normalizado for marcador in cls._MARCADORES_CAMPANHA)

    @staticmethod
    def _normalizar_regioes(
        regioes,
    ) -> tuple[str, ...]:
        resultado: list[str] = []
        vistos: set[str] = set()

        for regiao in regioes or ():

            valor = str(regiao or "").strip().upper()

            if not valor:
                continue

            if valor in vistos:
                continue

            vistos.add(valor)

            resultado.append(valor)

        return tuple(resultado)

    @staticmethod
    def _normalizar_termos(
        termos,
    ) -> tuple[str, ...]:
        resultado: list[str] = []
        vistos: set[str] = set()

        for termo in termos or ():

            valor = str(termo or "").strip()

            if not valor:
                continue

            chave = valor.casefold()

            if chave in vistos:
                continue

            vistos.add(chave)

            resultado.append(valor)

        return tuple(resultado)

    @staticmethod
    def _obter_marketplace(
        *,
        resolucao: ResolucaoScout | None,
        plano: PlanoDiscoveryScout | None,
    ) -> str | None:
        candidatos = []

        if resolucao is not None:
            candidatos.append(resolucao.marketplace)

        if plano is not None:
            candidatos.append(plano.marketplace)

        for candidato in candidatos:

            valor = str(candidato or "").strip().casefold()

            if valor:
                return valor

        return None

    @staticmethod
    def _validar_identidade(
        *,
        sinal: SinalScout,
        resolucao: ResolucaoScout | None,
        plano: PlanoDiscoveryScout | None,
    ) -> None:
        fonte = str(sinal.fonte or "").strip().casefold()

        id_externo = str(sinal.id_externo or "").strip()

        for nome, item in (
            (
                "resolucao",
                resolucao,
            ),
            (
                "plano",
                plano,
            ),
        ):
            if item is None:
                continue

            fonte_item = str(item.fonte or "").strip().casefold()

            id_item = str(item.id_externo or "").strip()

            if fonte_item != fonte or id_item != id_externo:
                raise ValueError("Identidade inconsistente entre " f"SinalScout e {nome}.")
