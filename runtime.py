# 63.8738, -149.7525

"""Ponto único de inicialização do Projeto Renda Automática.

Execução:
    python runtime.py

O runtime mantém o bot de consulta ativo e dispara o pipeline no
intervalo configurado. O pipeline continua usando o launcher existente
para preparar Chrome/CDP e a trava própria de execução.
"""

from __future__ import annotations

import logging
import os

from config.logging_config import configurar_logging
from repositories.user_identity_repository import UserIdentityRepository
from repositories.user_personalization_repository import (
    UserPersonalizationRepository,
)
from services.api_aplicacao.controlador import ControladorApiAplicacao
from services.api_aplicacao.servidor import ServidorApiAplicacao
from services.community_moderation_read_service import CommunityModerationReadService
from services.community_moderation_runtime import (
    ResultadoAtivacaoCommunityModeration,
    ativar_community_moderation_runtime,
)
from services.controle.servidor_status import ServidorStatusAdministrativo
from services.gamification_read_service import GamificationReadService
from services.gamification_runtime import ativar_gamificacao_runtime
from services.launcher.chrome_launcher import encerrar_chrome_automacao
from services.mission_read_service import MissionReadService
from services.mission_reward_settlement_runtime import (
    ativar_reward_settlement_runtime,
)
from services.mission_runtime import ativar_missoes_runtime
from services.personalized_feed_service import PersonalizedFeedService
from services.runtime.orquestrador import (
    DIRETORIO_PROJETO,
    ConfiguracoesRuntime,
    OrquestradorRuntime,
    TravaRuntime,
)
from services.user_identity_service import UserIdentityService
from services.user_personalization_service import UserPersonalizationService

logger = logging.getLogger(__name__)


def _ativar_community_moderation_controlado(
    *,
    caminho_banco: str,
) -> ResultadoAtivacaoCommunityModeration:
    resultado = ativar_community_moderation_runtime(
        caminho_banco=caminho_banco,
        permitir_schema_activation=True,
        executar_reconciliation=False,
    )

    if resultado.ativo:
        logger.info(
            "Community Moderation runtime ativo | " "reconciliation_executada=%s",
            resultado.reconciliation_executada,
        )

    elif resultado.erro == "feature_flag_disabled":
        logger.info("Community Moderation runtime desativado " "por feature flag.")

    else:
        logger.error(
            "Community Moderation runtime inativo | erro=%s",
            resultado.erro,
        )

    return resultado


def main() -> int:
    os.chdir(DIRETORIO_PROJETO)
    os.environ["RADAR_MANTER_CHROME_ATIVO"] = "1"
    os.environ["RADAR_CDP_EXTERNO"] = "1"
    configurar_logging()

    print("=" * 68)
    print("PROJETO RENDA AUTOMÁTICA")
    print("Runtime Unificado v1")
    print("=" * 68)

    try:
        configuracoes = ConfiguracoesRuntime.carregar()
    except ValueError as erro:
        logger.error("Configuração inválida do runtime: %s", erro)
        return 2

    trava = TravaRuntime(configuracoes.porta_trava)

    if not trava.adquirir():
        logger.error(
            "Já existe outro runtime ativo usando a porta local %s.",
            configuracoes.porta_trava,
        )
        return 75

    orquestrador = OrquestradorRuntime(configuracoes)
    servidor_status = ServidorStatusAdministrativo(
        controlador=orquestrador.controle_administrativo,
    )
    controlador_api = ControladorApiAplicacao()
    user_identity_db = os.path.join(
        DIRETORIO_PROJETO,
        "database",
        "user_identity.sqlite3",
    )
    user_identity_repository = UserIdentityRepository(
        user_identity_db,
    )
    user_identity_service = UserIdentityService(
        user_identity_repository,
    )
    community_moderation_read_service = CommunityModerationReadService(user_identity_db)

    servidor_status.community_moderation_read_service = community_moderation_read_service

    user_personalization_repository = UserPersonalizationRepository(
        user_identity_db,
    )
    user_personalization_service = UserPersonalizationService(
        user_personalization_repository,
        user_identity_repository,
    )

    gamification_runtime = ativar_gamificacao_runtime(
        caminho_banco=user_identity_db,
        user_identity_repository=(user_identity_repository),
        user_identity_service=(user_identity_service),
        user_personalization_repository=(user_personalization_repository),
        user_personalization_service=(user_personalization_service),
    )

    gamification_read_service = None

    if gamification_runtime.ativo:
        reconciliacao = gamification_runtime.reconciliacao

        if gamification_runtime.service is not None:
            gamification_read_service = GamificationReadService(gamification_runtime.service)

        logger.info(
            "Gamification runtime ativo | " "contas=%s criados=%s " "idempotentes=%s",
            (reconciliacao.contas_processadas if reconciliacao is not None else 0),
            (reconciliacao.eventos_criados if reconciliacao is not None else 0),
            (reconciliacao.eventos_idempotentes if reconciliacao is not None else 0),
        )
    else:
        logger.error(
            "Gamification runtime inativo | erro=%s",
            gamification_runtime.erro,
        )
    mission_read_service = None

    mission_runtime = ativar_missoes_runtime(
        caminho_banco=user_identity_db,
        user_identity_repository=(user_identity_repository),
    )

    if mission_runtime.ativo:
        os.environ["MISSIONS_COMMUNITY_RUNTIME_ATIVO"] = "1"

        if mission_runtime.service is not None:
            mission_read_service = MissionReadService(
                mission_runtime.service,
            )

        mission_reconciliacao = mission_runtime.reconciliacao

        logger.info(
            "Missions runtime ativo | " "descobertas=%s criados=%s " "idempotentes=%s rewards=%s",
            (
                mission_reconciliacao.descobertas_processadas
                if mission_reconciliacao is not None
                else 0
            ),
            (mission_reconciliacao.eventos_criados if mission_reconciliacao is not None else 0),
            (
                mission_reconciliacao.eventos_idempotentes
                if mission_reconciliacao is not None
                else 0
            ),
            (mission_reconciliacao.recompensas_criadas if mission_reconciliacao is not None else 0),
        )

    else:
        os.environ["MISSIONS_COMMUNITY_RUNTIME_ATIVO"] = "0"

        logger.error(
            "Missions runtime inativo | " "erro=%s",
            mission_runtime.erro,
        )

    reward_settlement_runtime = None

    if configuracoes.mission_reward_settlement_ativo:
        prerequisites_ok = (
            gamification_runtime.ativo
            and mission_runtime.ativo
            and mission_runtime.service is not None
        )

        if prerequisites_ok:
            reward_settlement_runtime = ativar_reward_settlement_runtime(
                caminho_banco=user_identity_db,
                user_identity_repository=(user_identity_repository),
                mission_service=(mission_runtime.service),
            )

            settlement_reconciliacao = reward_settlement_runtime.reconciliacao

            if reward_settlement_runtime.ativo:
                logger.info(
                    "Mission reward settlement ativo | "
                    "pendentes=%s eventos_criados=%s "
                    "eventos_idempotentes=%s "
                    "rewards_marcados=%s",
                    (
                        settlement_reconciliacao.recompensas_encontradas
                        if settlement_reconciliacao is not None
                        else 0
                    ),
                    (
                        settlement_reconciliacao.eventos_criados
                        if settlement_reconciliacao is not None
                        else 0
                    ),
                    (
                        settlement_reconciliacao.eventos_idempotentes
                        if settlement_reconciliacao is not None
                        else 0
                    ),
                    (
                        settlement_reconciliacao.recompensas_marcadas
                        if settlement_reconciliacao is not None
                        else 0
                    ),
                )

            else:
                logger.error(
                    "Mission reward settlement inativo | erro=%s",
                    reward_settlement_runtime.erro,
                )

        else:
            logger.error(
                "Mission reward settlement bloqueado | "
                "gamification_ativo=%s missions_ativo=%s "
                "mission_service=%s",
                gamification_runtime.ativo,
                mission_runtime.ativo,
                mission_runtime.service is not None,
            )

    else:
        logger.info("Mission reward settlement desativado por feature flag.")

    community_moderation_resultado = _ativar_community_moderation_controlado(
        caminho_banco=user_identity_db,
    )

    if community_moderation_resultado.ativo and (
        community_moderation_resultado.componentes is not None
    ):
        servidor_status.community_moderation_decision_service = (
            community_moderation_resultado.componentes.moderation_service
        )

    else:
        servidor_status.community_moderation_decision_service = None

    personalized_feed_service = PersonalizedFeedService(
        catalogo_repository=controlador_api.catalogo_repository,
        price_intelligence_repository=controlador_api.price_intelligence_repository,
        user_personalization_service=user_personalization_service,
    )
    servidor_api = ServidorApiAplicacao(
        controlador=controlador_api,
        user_identity_service=user_identity_service,
        user_personalization_service=user_personalization_service,
        personalized_feed_service=personalized_feed_service,
        gamification_read_service=gamification_read_service,
        mission_read_service=mission_read_service,
    )

    try:
        servidor_status.iniciar()
        servidor_api.iniciar()
        orquestrador.executar()
        return 0

    except KeyboardInterrupt:
        print()
        logger.info("Interrupção solicitada pelo usuário.")
        return 130

    except Exception:
        logger.exception("Falha não tratada no runtime.")
        return 1

    finally:
        servidor_api.encerrar()
        servidor_status.encerrar()
        orquestrador.encerrar()

        try:
            encerrar_chrome_automacao()
        except Exception:
            logger.exception("Falha ao encerrar o Chrome persistente durante o desligamento.")

        trava.liberar()


if __name__ == "__main__":
    raise SystemExit(main())
