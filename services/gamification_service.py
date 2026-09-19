from __future__ import annotations

from datetime import (
    UTC,
    datetime,
    timedelta,
)
from typing import Any

from models.gamification import (
    EventoGamificacao,
    PerfilGamificacao,
    ResultadoEventoGamificacao,
)
from repositories.gamification_repository import (
    ConflitoIdempotenciaGamificacao,
    GamificationRepository,
    LimiteEventosGamificacaoExcedido,
)
from repositories.user_identity_repository import (
    UserIdentityRepository,
)
from services.gamification_rules import (
    ConjuntoRegrasGamificacao,
)


class EventoGamificacaoDesconhecido(ValueError):
    pass


class LimiteGamificacaoExcedido(ValueError):
    pass


class ContaGamificacaoInvalida(ValueError):
    pass


class ConflitoEventoGamificacao(ValueError):
    pass


class GamificationService:
    def __init__(
        self,
        repository: GamificationRepository,
        identity_repository: UserIdentityRepository,
        ruleset: ConjuntoRegrasGamificacao,
    ) -> None:
        self.repository = repository
        self.identity_repository = identity_repository
        self.ruleset = ruleset

    def _validar_conta_ativa(
        self,
        conta_id: str,
    ) -> str:
        conta = str(conta_id or "").strip()

        if not conta:
            raise ContaGamificacaoInvalida("conta_id nao pode ser vazio.")

        registro = self.identity_repository.obter_conta(conta)

        if registro is None or not bool(
            getattr(
                registro,
                "ativa",
                True,
            )
        ):
            raise ContaGamificacaoInvalida("Conta inexistente ou inativa.")

        return conta

    def _perfil(
        self,
        conta_id: str,
    ) -> PerfilGamificacao:
        saldo = self.repository.obter_saldo(conta_id)

        return PerfilGamificacao(
            conta_id=saldo.conta_id,
            xp_total=saldo.xp_total,
            reputacao_total=(saldo.reputacao_total),
            nivel=(self.ruleset.calcular_nivel(saldo.xp_total)),
            eventos_total=(saldo.eventos_total),
            atualizado_em=(saldo.atualizado_em),
        )

    def obter_perfil(
        self,
        conta_id: str,
    ) -> PerfilGamificacao:
        conta = self._validar_conta_ativa(conta_id)

        return self._perfil(conta)

    def listar_eventos(
        self,
        conta_id: str,
        *,
        limite: int = 50,
        offset: int = 0,
    ) -> list[EventoGamificacao]:
        conta = self._validar_conta_ativa(conta_id)

        return self.repository.listar_eventos(
            conta_id=conta,
            limite=limite,
            offset=offset,
        )

    def registrar_evento(
        self,
        *,
        conta_id: str,
        chave_idempotencia: str,
        tipo_evento: str,
        origem: str,
        origem_id: str | None = None,
        metadados: dict[str, Any] | None = None,
        ocorrido_em: datetime | None = None,
    ) -> ResultadoEventoGamificacao:
        conta = self._validar_conta_ativa(conta_id)

        chave = str(chave_idempotencia or "").strip()

        if not chave:
            raise ValueError("chave_idempotencia " "nao pode ser vazia.")

        tipo = str(tipo_evento or "").strip()

        regra = self.ruleset.obter_regra(tipo)

        if regra is None:
            raise (EventoGamificacaoDesconhecido("Evento sem regra " f"versionada: {tipo!r}."))

        origem_normalizada = str(origem or "").strip()

        if not origem_normalizada:
            raise ValueError("origem nao pode ser vazia.")

        agora = datetime.now(UTC)

        instante = ocorrido_em or agora

        if instante.tzinfo is None:
            raise ValueError("ocorrido_em precisa " "possuir timezone.")

        instante_utc = instante.astimezone(UTC)

        limite = regra.limite_por_janela

        desde_iso = None

        if limite is not None and regra.janela_segundos is not None:
            desde = agora - timedelta(seconds=(regra.janela_segundos))

            desde_iso = desde.isoformat(timespec="seconds")

        try:
            evento, criado = self.repository.registrar_evento(
                conta_id=conta,
                chave_idempotencia=chave,
                tipo_evento=(regra.tipo_evento),
                origem=(origem_normalizada),
                origem_id=(
                    str(origem_id).strip()
                    if (origem_id is not None and str(origem_id).strip())
                    else None
                ),
                xp_delta=(regra.xp_delta),
                reputacao_delta=(regra.reputacao_delta),
                regra_versao=(self.ruleset.versao),
                metadados=metadados,
                ocorrido_em=(instante_utc.isoformat(timespec="seconds")),
                limite_por_janela=(limite),
                desde_iso=desde_iso,
            )

        except ConflitoIdempotenciaGamificacao as erro:
            raise ConflitoEventoGamificacao(
                "Chave de idempotencia reutilizada " "com semantica diferente."
            ) from erro

        except LimiteEventosGamificacaoExcedido as erro:
            raise (
                LimiteGamificacaoExcedido(
                    "Limite anti-farming " "atingido para " f"{regra.tipo_evento!r}."
                )
            ) from erro

        return ResultadoEventoGamificacao(
            evento=evento,
            perfil=self._perfil(conta),
            criado=criado,
        )
