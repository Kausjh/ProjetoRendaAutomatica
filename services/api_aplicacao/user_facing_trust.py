from __future__ import annotations

from models.community_trust import (
    ResumoEvidenciaCommunityTrust,
)
from models.user_identity import (
    ContaUsuario,
)
from services.api_aplicacao.user_facing_http import (
    ErroHttpUserFacing,
)
from services.community_trust_read_service import (
    CommunityTrustReadService,
    CommunityTrustReadUnavailableError,
    HistoricoCommunityTrustUsuario,
    LeituraCommunityTrustUsuario,
)


class UserFacingCommunityTrustController:
    def __init__(
        self,
        read_service: CommunityTrustReadService | None,
    ) -> None:
        self.read_service = read_service

    def _service(
        self,
    ) -> CommunityTrustReadService:
        service = self.read_service

        if service is None:
            raise ErroHttpUserFacing(
                503,
                "trust_comunitario_indisponivel",
                "Trust comunitario indisponivel.",
            )

        return service

    @staticmethod
    def _validar_conta(
        conta: ContaUsuario,
    ) -> None:
        if not conta.ativa:
            raise ErroHttpUserFacing(
                401,
                "sessao_usuario_invalida",
                "Sessao de usuario invalida.",
            )

    @staticmethod
    def _paginacao_historico(
        *,
        limite: object,
        offset: object,
    ) -> tuple[
        int,
        int,
    ]:
        try:
            limite_int = int(str(limite).strip())

            offset_int = int(str(offset).strip())

        except (
            TypeError,
            ValueError,
        ) as erro:
            raise ErroHttpUserFacing(
                400,
                "paginacao_trust_invalida",
                "Paginacao de Trust invalida.",
            ) from erro

        if limite_int < 1 or limite_int > 100 or offset_int < 0:
            raise ErroHttpUserFacing(
                400,
                "paginacao_trust_invalida",
                ("limite deve estar entre 1 e 100 " "e offset deve ser maior ou igual a zero."),
            )

        return (
            limite_int,
            offset_int,
        )

    @staticmethod
    def _serializar(
        leitura: LeituraCommunityTrustUsuario,
    ) -> dict[
        str,
        object,
    ]:
        perfil = leitura.perfil

        return {
            "perfil": {
                "evidencias_total": int(perfil.evidencias_total),
                "positivas_total": int(perfil.positivas_total),
                "negativas_total": int(perfil.negativas_total),
                "neutras_total": int(perfil.neutras_total),
                "atualizado_em": perfil.atualizado_em,
            },
            "modelo": {
                "versao": int(leitura.read_model_version),
                "score_numerico_definido": False,
            },
        }

    @staticmethod
    def _serializar_evidencia(
        evidencia: ResumoEvidenciaCommunityTrust,
    ) -> dict[
        str,
        object,
    ]:
        return {
            "tipo_evidencia": evidencia.tipo_evidencia,
            "classificacao": evidencia.classificacao,
            "ocorrido_em": evidencia.ocorrido_em,
        }

    @classmethod
    def _serializar_historico(
        cls,
        historico: HistoricoCommunityTrustUsuario,
    ) -> dict[
        str,
        object,
    ]:
        itens = [cls._serializar_evidencia(evidencia) for evidencia in historico.itens]

        return {
            "itens": itens,
            "limite": int(historico.limite),
            "offset": int(historico.offset),
            "quantidade": len(itens),
        }

    def obter(
        self,
        conta: ContaUsuario,
    ) -> tuple[
        int,
        dict[
            str,
            object,
        ],
    ]:
        self._validar_conta(conta)

        try:
            leitura = self._service().obter(conta.id)

        except CommunityTrustReadUnavailableError as erro:
            raise ErroHttpUserFacing(
                503,
                "trust_comunitario_indisponivel",
                "Trust comunitario indisponivel.",
            ) from erro

        except ValueError as erro:
            raise ErroHttpUserFacing(
                400,
                "trust_comunitario_invalido",
                "Leitura de Trust invalida.",
            ) from erro

        return (
            200,
            self._serializar(leitura),
        )

    def listar_evidencias(
        self,
        conta: ContaUsuario,
        *,
        limite: object = "20",
        offset: object = "0",
    ) -> tuple[
        int,
        dict[
            str,
            object,
        ],
    ]:
        self._validar_conta(conta)

        limite_int, offset_int = self._paginacao_historico(
            limite=limite,
            offset=offset,
        )

        try:
            historico = self._service().listar_evidencias(
                conta_id=conta.id,
                limite=limite_int,
                offset=offset_int,
            )

        except CommunityTrustReadUnavailableError as erro:
            raise ErroHttpUserFacing(
                503,
                "trust_comunitario_indisponivel",
                "Historico de Trust indisponivel.",
            ) from erro

        except ValueError as erro:
            raise ErroHttpUserFacing(
                400,
                "paginacao_trust_invalida",
                "Paginacao de Trust invalida.",
            ) from erro

        return (
            200,
            self._serializar_historico(historico),
        )
