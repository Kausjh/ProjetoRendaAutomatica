from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from repositories.gamification_reconciliation_repository import (
    GamificationReconciliationRepository,
)
from services.gamification_event_wiring import (
    GamificationEventWiring,
    ResultadoWiringGamificacao,
)


@dataclass(frozen=True, slots=True)
class ResultadoReconciliacaoGamificacao:
    contas_processadas: int
    eventos_criados: int
    eventos_idempotentes: int
    falhas: tuple[str, ...]

    @property
    def sucesso(
        self,
    ) -> bool:
        return not self.falhas


class GamificationReconciliationService:
    def __init__(
        self,
        repository: GamificationReconciliationRepository,
        wiring: GamificationEventWiring,
    ) -> None:
        self.repository = repository
        self.wiring = wiring

    @staticmethod
    def _data(
        valor: str | None,
    ) -> datetime | None:
        texto = str(valor or "").strip()

        if not texto:
            return None

        try:
            return datetime.fromisoformat(texto)
        except ValueError:
            return None

    def reconciliar(
        self,
    ) -> ResultadoReconciliacaoGamificacao:
        criados = 0
        idempotentes = 0
        falhas: list[str] = []

        def aplicar(
            *,
            conta_id: str,
            descricao: str,
            resultado: ResultadoWiringGamificacao,
        ) -> None:
            nonlocal criados
            nonlocal idempotentes

            if resultado.status == "created":
                criados += 1
                return

            if resultado.status == "idempotent":
                idempotentes += 1
                return

            falhas.append(f"{conta_id}:{descricao}:" f"{resultado.status}")

        contas = self.repository.listar_contas_ativas()

        for conta in contas:
            aplicar(
                conta_id=conta.conta_id,
                descricao=("onboarding_conta_criada"),
                resultado=(
                    self.wiring.registrar_conta_criada(
                        conta_id=conta.conta_id,
                        ocorrido_em=self._data(conta.criado_em),
                    )
                ),
            )

            dispositivo_em = self.repository.obter_primeiro_dispositivo_em(conta.conta_id)

            if dispositivo_em is not None:
                aplicar(
                    conta_id=conta.conta_id,
                    descricao=("onboarding_dispositivo_vinculado"),
                    resultado=(
                        self.wiring.registrar_primeiro_dispositivo(
                            conta_id=(conta.conta_id),
                            ocorrido_em=(self._data(dispositivo_em)),
                        )
                    ),
                )

            preferencias_em = self.repository.obter_preferencias_em(conta.conta_id)

            if preferencias_em is not None:
                aplicar(
                    conta_id=conta.conta_id,
                    descricao=("onboarding_preferencias_definidas"),
                    resultado=(
                        self.wiring.registrar_preferencias_definidas(
                            conta_id=(conta.conta_id),
                            ocorrido_em=(self._data(preferencias_em)),
                        )
                    ),
                )

            itens = self.repository.listar_watchlist(conta.conta_id)

            for item in itens:
                aplicar(
                    conta_id=conta.conta_id,
                    descricao=("watchlist_produto_adicionado:" + item.canonical_key),
                    resultado=(
                        self.wiring.registrar_produto_watchlist(
                            conta_id=(conta.conta_id),
                            canonical_key=(item.canonical_key),
                            ocorrido_em=(self._data(item.criado_em)),
                        )
                    ),
                )

                if item.possui_preco_alvo:
                    aplicar(
                        conta_id=(conta.conta_id),
                        descricao=("watchlist_preco_alvo_definido:" + item.canonical_key),
                        resultado=(
                            self.wiring.registrar_preco_alvo(
                                conta_id=(conta.conta_id),
                                canonical_key=(item.canonical_key),
                                ocorrido_em=(self._data(item.atualizado_em)),
                            )
                        ),
                    )

        return ResultadoReconciliacaoGamificacao(
            contas_processadas=len(contas),
            eventos_criados=criados,
            eventos_idempotentes=(idempotentes),
            falhas=tuple(falhas),
        )
