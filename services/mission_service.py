from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from models.missions import (
    ConcessaoRecompensaMissao,
    ProgressoMissao,
    ResultadoProgressoMissao,
)
from repositories.mission_repository import (
    ConflitoConcessaoRecompensa,
    ConflitoEstadoMissao,
    ConflitoIdempotenciaMissao,
    MissionRepository,
)
from repositories.user_identity_repository import (
    UserIdentityRepository,
)
from services.mission_rules import (
    ConjuntoRegrasMissoes,
)


class MissaoDesconhecida(ValueError):
    pass


class ContaMissaoInvalida(ValueError):
    pass


class EventoMissaoInvalido(ValueError):
    pass


class ConflitoEventoMissao(ValueError):
    pass


class ConflitoRecompensaMissao(ValueError):
    pass


class MissionService:
    def __init__(
        self,
        repository: MissionRepository,
        identity_repository: UserIdentityRepository,
        ruleset: ConjuntoRegrasMissoes,
    ) -> None:
        self.repository = repository
        self.identity_repository = identity_repository
        self.ruleset = ruleset

    @staticmethod
    def _agora() -> str:
        return datetime.now(UTC).isoformat()

    def _validar_conta(
        self,
        conta_id: str,
    ) -> str:
        conta = str(conta_id or "").strip()

        if not conta:
            raise ContaMissaoInvalida("conta_id nao pode ser vazio.")

        registro = self.identity_repository.obter_conta(conta)

        if registro is None or not registro.ativa:
            raise ContaMissaoInvalida("Conta inexistente ou inativa.")

        return conta

    def obter_progresso(
        self,
        *,
        conta_id: str,
        missao_codigo: str,
        instancia_chave: str = "lifetime",
    ) -> ProgressoMissao | None:
        conta = self._validar_conta(conta_id)

        missao = self.ruleset.obter(missao_codigo)

        if missao is None:
            raise MissaoDesconhecida("Missao desconhecida.")

        return self.repository.obter_progresso(
            conta_id=conta,
            missao_codigo=missao.codigo,
            regra_versao=self.ruleset.versao,
            instancia_chave=(str(instancia_chave or "").strip() or "lifetime"),
        )

    def listar_progressos(
        self,
        *,
        conta_id: str,
    ) -> list[ProgressoMissao]:
        conta = self._validar_conta(conta_id)

        return self.repository.listar_progressos(conta_id=conta)

    def registrar_evento(
        self,
        *,
        conta_id: str,
        missao_codigo: str,
        tipo_evento: str,
        origem: str,
        origem_id: str,
        chave_idempotencia: str,
        instancia_chave: str = "lifetime",
        metadados: dict[str, Any] | None = None,
        ocorrido_em: str | None = None,
    ) -> ResultadoProgressoMissao:
        conta = self._validar_conta(conta_id)

        missao = self.ruleset.obter(missao_codigo)

        if missao is None:
            raise MissaoDesconhecida("Missao desconhecida.")

        evento = str(tipo_evento or "").strip()

        if evento != missao.tipo_evento:
            raise EventoMissaoInvalido("Evento nao corresponde " "a missao.")

        origem_normalizada = str(origem or "").strip()

        origem_id_normalizado = str(origem_id or "").strip()

        chave = str(chave_idempotencia or "").strip()

        instancia = str(instancia_chave or "").strip()

        if not origem_normalizada:
            raise ValueError("origem nao pode ser vazia.")

        if not origem_id_normalizado:
            raise ValueError("origem_id nao pode ser vazio.")

        if not chave:
            raise ValueError("chave_idempotencia " "nao pode ser vazia.")

        if not instancia:
            raise ValueError("instancia_chave " "nao pode ser vazia.")

        try:
            return self.repository.registrar_progresso(
                conta_id=conta,
                missao_codigo=missao.codigo,
                regra_versao=(self.ruleset.versao),
                instancia_chave=instancia,
                chave_idempotencia=chave,
                tipo_evento=evento,
                origem=origem_normalizada,
                origem_id=(origem_id_normalizado),
                delta=(missao.incremento_por_evento),
                alvo_total=missao.alvo,
                recompensa_xp=(missao.recompensa_xp),
                metadados=dict(metadados or {}),
                ocorrido_em=(ocorrido_em or self._agora()),
            )

        except (
            ConflitoIdempotenciaMissao,
            ConflitoEstadoMissao,
        ) as erro:
            raise ConflitoEventoMissao(str(erro)) from erro

    def obter_recompensa(
        self,
        *,
        conta_id: str,
        missao_codigo: str,
        instancia_chave: str = "lifetime",
    ) -> ConcessaoRecompensaMissao | None:
        conta = self._validar_conta(conta_id)

        missao = self.ruleset.obter(missao_codigo)

        if missao is None:
            raise MissaoDesconhecida("Missao desconhecida.")

        return self.repository.obter_recompensa(
            conta_id=conta,
            missao_codigo=missao.codigo,
            regra_versao=self.ruleset.versao,
            instancia_chave=(str(instancia_chave or "").strip() or "lifetime"),
        )

    def listar_recompensas_pendentes(
        self,
        *,
        limite: int = 100,
    ) -> list[ConcessaoRecompensaMissao]:
        return self.repository.listar_recompensas_pendentes(limite=limite)

    def marcar_recompensa_concedida(
        self,
        *,
        recompensa_id: str,
        referencia_concessao: str,
    ) -> tuple[
        ConcessaoRecompensaMissao,
        bool,
    ]:
        try:
            return self.repository.marcar_recompensa_concedida(
                recompensa_id=(recompensa_id),
                referencia_concessao=(referencia_concessao),
            )

        except ConflitoConcessaoRecompensa as erro:
            raise ConflitoRecompensaMissao(str(erro)) from erro
