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
from services.controle.servidor_status import ServidorStatusAdministrativo
from services.gamification_read_service import GamificationReadService
from services.gamification_runtime import ativar_gamificacao_runtime
from services.launcher.chrome_launcher import encerrar_chrome_automacao
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
    mission_runtime = ativar_missoes_runtime(
        caminho_banco=user_identity_db,
        user_identity_repository=(user_identity_repository),
    )

    if mission_runtime.ativo:
        os.environ["MISSIONS_COMMUNITY_RUNTIME_ATIVO"] = "1"

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
