from __future__ import annotations

from dataclasses import dataclass

from models.missions import (
    ConcessaoRecompensaMissao,
)
from services.gamification_production_rules import (
    criar_ruleset_producao_v1,
)
from services.gamification_rules import (
    ConjuntoRegrasGamificacao,
    RegraGamificacao,
)
from services.gamification_service import (
    GamificationService,
)
from services.mission_production_catalog import (
    CatalogoMissoesProducao,
    criar_catalogo_missoes_producao_v1,
)
from services.mission_service import (
    MissionService,
)

SETTLEMENT_RULESET_VERSION = (
    "gamification-reputation-production-v1" "+missions-community-rewards-settlement-v1"
)

SETTLEMENT_ORIGIN = "missions-community-rewards-v1"

SETTLEMENT_KEY_PREFIX = "v1:mission-reward-settlement:"


@dataclass(frozen=True, slots=True)
class ResultadoLiquidacaoRecompensa:
    recompensa_id: str
    gamification_event_id: str
    evento_criado: bool
    recompensa_marcada: bool
    xp: int


@dataclass(frozen=True, slots=True)
class ResultadoLiquidacaoLote:
    recompensas_encontradas: int
    eventos_criados: int
    eventos_idempotentes: int
    recompensas_marcadas: int
    recompensas_idempotentes: int
    falhas: tuple[str, ...]


def criar_ruleset_gamificacao_com_rewards_missoes_v1(
    catalogo: CatalogoMissoesProducao | None = None,
) -> ConjuntoRegrasGamificacao:
    catalogo_real = catalogo or criar_catalogo_missoes_producao_v1()

    base = criar_ruleset_producao_v1()

    eventos_base = {regra.tipo_evento for regra in base.regras}

    regras_rewards: list[RegraGamificacao] = []

    for politica in catalogo_real.recompensas:
        if politica.evento_gamificacao in eventos_base:
            raise ValueError("Evento de reward colide com " "evento base de gamificacao.")

        regras_rewards.append(
            RegraGamificacao(
                tipo_evento=(politica.evento_gamificacao),
                xp_delta=politica.xp,
                reputacao_delta=0,
            )
        )

    return ConjuntoRegrasGamificacao(
        versao=SETTLEMENT_RULESET_VERSION,
        regras=(tuple(base.regras) + tuple(regras_rewards)),
        niveis_xp=base.niveis_xp,
    )


class MissionRewardSettlementService:
    def __init__(
        self,
        *,
        mission_service: MissionService,
        gamification_service: GamificationService,
        catalogo: CatalogoMissoesProducao,
    ) -> None:
        self.mission_service = mission_service

        self.gamification_service = gamification_service

        self.catalogo = catalogo

    @staticmethod
    def chave_idempotencia(
        recompensa_id: str,
    ) -> str:
        reward_id = str(recompensa_id or "").strip()

        if not reward_id:
            raise ValueError("recompensa_id nao pode ser vazio.")

        return SETTLEMENT_KEY_PREFIX + reward_id

    def _validar_recompensa(
        self,
        recompensa: ConcessaoRecompensaMissao,
    ):
        if recompensa.status != "pending":
            raise ValueError("Settlement aceita apenas " "recompensa pending.")

        if recompensa.tipo_recompensa != "xp":
            raise ValueError("Settlement V1 aceita apenas XP.")

        if recompensa.regra_versao != self.catalogo.ruleset.versao:
            raise ValueError("Ruleset da recompensa diverge " "do catalogo de producao.")

        instancia = self.catalogo.derivar_instancia_chave(recompensa.missao_codigo)

        if recompensa.instancia_chave != instancia:
            raise ValueError("Instancia da recompensa diverge " "da politica da missao.")

        politica = self.catalogo.recompensa_para(recompensa.missao_codigo)

        if recompensa.quantidade != politica.xp:
            raise ValueError("Quantidade de XP diverge " "da politica da missao.")

        return politica

    def liquidar_recompensa(
        self,
        recompensa: ConcessaoRecompensaMissao,
    ) -> ResultadoLiquidacaoRecompensa:
        politica = self._validar_recompensa(recompensa)

        chave = self.chave_idempotencia(recompensa.id)

        resultado_evento = self.gamification_service.registrar_evento(
            conta_id=recompensa.conta_id,
            chave_idempotencia=chave,
            tipo_evento=(politica.evento_gamificacao),
            origem=SETTLEMENT_ORIGIN,
            origem_id=recompensa.id,
            metadados={
                "reward_grant_id": (recompensa.id),
                "mission_code": (recompensa.missao_codigo),
                "mission_ruleset_version": (recompensa.regra_versao),
                "mission_instance_key": (recompensa.instancia_chave),
                "reward_type": (recompensa.tipo_recompensa),
                "reward_amount": (recompensa.quantidade),
            },
        )

        recompensa_atualizada, alterou = self.mission_service.marcar_recompensa_concedida(
            recompensa_id=recompensa.id,
            referencia_concessao=(resultado_evento.evento.id),
        )

        if recompensa_atualizada.status != "granted":
            raise RuntimeError("Reward nao terminou como granted.")

        if recompensa_atualizada.referencia_concessao != resultado_evento.evento.id:
            raise RuntimeError("Referencia de settlement " "diverge do evento.")

        return ResultadoLiquidacaoRecompensa(
            recompensa_id=recompensa.id,
            gamification_event_id=(resultado_evento.evento.id),
            evento_criado=(resultado_evento.criado),
            recompensa_marcada=alterou,
            xp=recompensa.quantidade,
        )

    def liquidar_pendentes(
        self,
        *,
        limite: int = 100,
    ) -> ResultadoLiquidacaoLote:
        pendentes = self.mission_service.listar_recompensas_pendentes(limite=limite)

        eventos_criados = 0
        eventos_idempotentes = 0
        recompensas_marcadas = 0
        recompensas_idempotentes = 0
        falhas: list[str] = []

        for recompensa in pendentes:
            try:
                resultado = self.liquidar_recompensa(recompensa)

                if resultado.evento_criado:
                    eventos_criados += 1
                else:
                    eventos_idempotentes += 1

                if resultado.recompensa_marcada:
                    recompensas_marcadas += 1
                else:
                    recompensas_idempotentes += 1

            except Exception as erro:
                falhas.append(recompensa.id + ":" + type(erro).__name__ + ":" + str(erro))

        return ResultadoLiquidacaoLote(
            recompensas_encontradas=len(pendentes),
            eventos_criados=eventos_criados,
            eventos_idempotentes=(eventos_idempotentes),
            recompensas_marcadas=(recompensas_marcadas),
            recompensas_idempotentes=(recompensas_idempotentes),
            falhas=tuple(falhas),
        )
