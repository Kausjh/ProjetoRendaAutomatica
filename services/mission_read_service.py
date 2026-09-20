from __future__ import annotations

from dataclasses import dataclass

from services.mission_production_catalog import (
    CatalogoMissoesProducao,
    criar_catalogo_missoes_producao_v1,
)
from services.mission_service import MissionService


@dataclass(frozen=True, slots=True)
class LeituraRecompensaMissao:
    tipo: str
    quantidade: int
    status: str
    concedida_em: str | None


@dataclass(frozen=True, slots=True)
class LeituraMissaoUsuario:
    codigo: str
    titulo: str
    descricao: str
    progresso_atual: int
    progresso_alvo: int
    percentual: float
    concluida: bool
    concluida_em: str | None
    atualizado_em: str | None
    recompensa: LeituraRecompensaMissao


@dataclass(frozen=True, slots=True)
class ResumoMissoesUsuario:
    total: int
    concluidas: int
    em_andamento: int
    nao_iniciadas: int
    rewards_pending: int
    rewards_granted: int


@dataclass(frozen=True, slots=True)
class LeituraMissoesUsuario:
    ruleset_version: str
    instancia_chave: str
    resumo: ResumoMissoesUsuario
    missoes: tuple[LeituraMissaoUsuario, ...]


class MissionReadService:
    def __init__(
        self,
        mission_service: MissionService,
        catalogo: CatalogoMissoesProducao | None = None,
    ) -> None:
        self.mission_service = mission_service
        self.catalogo = catalogo or criar_catalogo_missoes_producao_v1()

    def obter(
        self,
        conta_id: str,
    ) -> LeituraMissoesUsuario:
        itens: list[LeituraMissaoUsuario] = []

        concluidas = 0
        em_andamento = 0
        nao_iniciadas = 0
        rewards_pending = 0
        rewards_granted = 0

        for politica in self.catalogo.recompensas:
            definicao = self.catalogo.ruleset.obter(politica.missao_codigo)

            if definicao is None:
                raise RuntimeError("Catalogo de reward referencia " "missao inexistente.")

            instancia = self.catalogo.derivar_instancia_chave(definicao.codigo)

            progresso = self.mission_service.obter_progresso(
                conta_id=conta_id,
                missao_codigo=definicao.codigo,
                instancia_chave=instancia,
            )

            recompensa = self.mission_service.obter_recompensa(
                conta_id=conta_id,
                missao_codigo=definicao.codigo,
                instancia_chave=instancia,
            )

            progresso_atual = 0 if progresso is None else int(progresso.progresso_total)

            progresso_atual = min(
                progresso_atual,
                int(definicao.alvo),
            )

            concluida = progresso is not None and progresso.concluida

            if recompensa is not None and not concluida:
                raise RuntimeError("Reward existe para missao " "nao concluida.")

            if concluida and recompensa is None:
                raise RuntimeError("Missao concluida sem reward.")

            if recompensa is None:
                reward_status = "locked"
                reward_concedida_em = None
            else:
                reward_status = recompensa.status
                reward_concedida_em = recompensa.concedida_em

            if reward_status == "pending":
                rewards_pending += 1

            if reward_status == "granted":
                rewards_granted += 1

            if concluida:
                concluidas += 1
            elif progresso_atual > 0:
                em_andamento += 1
            else:
                nao_iniciadas += 1

            percentual = round(
                (progresso_atual / int(definicao.alvo)) * 100.0,
                2,
            )

            itens.append(
                LeituraMissaoUsuario(
                    codigo=definicao.codigo,
                    titulo=definicao.titulo,
                    descricao=definicao.descricao,
                    progresso_atual=progresso_atual,
                    progresso_alvo=int(definicao.alvo),
                    percentual=percentual,
                    concluida=concluida,
                    concluida_em=(progresso.concluida_em if progresso is not None else None),
                    atualizado_em=(progresso.atualizado_em if progresso is not None else None),
                    recompensa=(
                        LeituraRecompensaMissao(
                            tipo="xp",
                            quantidade=int(politica.xp),
                            status=reward_status,
                            concedida_em=(reward_concedida_em),
                        )
                    ),
                )
            )

        return LeituraMissoesUsuario(
            ruleset_version=(self.catalogo.ruleset.versao),
            instancia_chave=(self.catalogo.instancia_chave),
            resumo=ResumoMissoesUsuario(
                total=len(itens),
                concluidas=concluidas,
                em_andamento=em_andamento,
                nao_iniciadas=nao_iniciadas,
                rewards_pending=rewards_pending,
                rewards_granted=rewards_granted,
            ),
            missoes=tuple(itens),
        )
