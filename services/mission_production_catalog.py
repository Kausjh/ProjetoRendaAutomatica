from __future__ import annotations

from dataclasses import dataclass

from services.mission_rules import (
    ConjuntoRegrasMissoes,
    DefinicaoMissao,
)

MISSION_RULESET_VERSION = "missions-community-rewards-production-v1"

COMMUNITY_APPROVED_EVENT = "community_discovery_approved"

COMMUNITY_APPROVED_ORIGIN = "community_discovery_v1"

INSTANCE_POLICY = "account_lifetime"
INSTANCE_KEY = "lifetime"

MAX_LIFETIME_REWARD_XP = 170


@dataclass(frozen=True, slots=True)
class PoliticaRecompensaMissao:
    missao_codigo: str
    evento_gamificacao: str
    xp: int

    def __post_init__(self) -> None:
        if not self.missao_codigo.strip():
            raise ValueError("missao_codigo nao pode ser vazio.")

        if not self.evento_gamificacao.strip():
            raise ValueError("evento_gamificacao " "nao pode ser vazio.")

        if self.xp < 1:
            raise ValueError("xp precisa ser positivo.")


@dataclass(frozen=True, slots=True)
class CatalogoMissoesProducao:
    ruleset: ConjuntoRegrasMissoes
    recompensas: tuple[PoliticaRecompensaMissao, ...]
    politica_instancia: str
    instancia_chave: str
    origem_evento: str

    def __post_init__(self) -> None:
        if self.politica_instancia != INSTANCE_POLICY:
            raise ValueError("Politica de instancia " "nao suportada na V1.")

        if self.instancia_chave != INSTANCE_KEY:
            raise ValueError("Instancia V1 precisa ser " "lifetime.")

        codigos = {missao.codigo for missao in self.ruleset.missoes}

        recompensas_por_codigo = {item.missao_codigo: item for item in self.recompensas}

        if len(recompensas_por_codigo) != len(self.recompensas):
            raise ValueError("Politicas de recompensa " "duplicadas.")

        if set(recompensas_por_codigo) != codigos:
            raise ValueError("Toda missao precisa ter " "uma politica de recompensa.")

        eventos = [item.evento_gamificacao for item in self.recompensas]

        if len(eventos) != len(set(eventos)):
            raise ValueError("Eventos de settlement " "precisam ser unicos.")

        total_xp = 0

        for missao in self.ruleset.missoes:
            if missao.tipo_evento != COMMUNITY_APPROVED_EVENT:
                raise ValueError("Catalogo V1 aceita apenas " "community approved.")

            politica = recompensas_por_codigo[missao.codigo]

            if politica.xp != missao.recompensa_xp:
                raise ValueError("XP da politica diverge " "da definicao da missao.")

            total_xp += politica.xp

        if total_xp > MAX_LIFETIME_REWARD_XP:
            raise ValueError("Catalogo excede teto de XP " "lifetime da V1.")

    @property
    def xp_total_lifetime(self) -> int:
        return sum(item.xp for item in self.recompensas)

    def recompensa_para(
        self,
        missao_codigo: str,
    ) -> PoliticaRecompensaMissao:
        codigo = str(missao_codigo or "").strip()

        for recompensa in self.recompensas:
            if recompensa.missao_codigo == codigo:
                return recompensa

        raise ValueError("Missao sem politica " "de recompensa.")

    def derivar_instancia_chave(
        self,
        missao_codigo: str,
    ) -> str:
        if self.ruleset.obter(missao_codigo) is None:
            raise ValueError("Missao desconhecida.")

        return self.instancia_chave

    def chave_idempotencia_aprovacao(
        self,
        discovery_id: str,
    ) -> str:
        discovery = str(discovery_id or "").strip()

        if not discovery:
            raise ValueError("discovery_id nao pode ser vazio.")

        return "v1:community-approved:" + discovery


def criar_catalogo_missoes_producao_v1() -> CatalogoMissoesProducao:
    ruleset = ConjuntoRegrasMissoes(
        versao=MISSION_RULESET_VERSION,
        missoes=(
            DefinicaoMissao(
                codigo=("community_primeira_aprovada"),
                titulo=("Primeira descoberta aprovada"),
                descricao=("Tenha uma oferta enviada " "pela comunidade aprovada " "pelo Radar."),
                tipo_evento=(COMMUNITY_APPROVED_EVENT),
                alvo=1,
                recompensa_xp=20,
            ),
            DefinicaoMissao(
                codigo=("community_cinco_aprovadas"),
                titulo=("Cinco descobertas aprovadas"),
                descricao=("Tenha cinco ofertas " "comunitarias aprovadas " "pelo Radar."),
                tipo_evento=(COMMUNITY_APPROVED_EVENT),
                alvo=5,
                recompensa_xp=50,
            ),
            DefinicaoMissao(
                codigo=("community_dez_aprovadas"),
                titulo=("Dez descobertas aprovadas"),
                descricao=("Tenha dez ofertas " "comunitarias aprovadas " "pelo Radar."),
                tipo_evento=(COMMUNITY_APPROVED_EVENT),
                alvo=10,
                recompensa_xp=100,
            ),
        ),
    )

    recompensas = (
        PoliticaRecompensaMissao(
            missao_codigo=("community_primeira_aprovada"),
            evento_gamificacao=("mission_reward_" "community_primeira_aprovada"),
            xp=20,
        ),
        PoliticaRecompensaMissao(
            missao_codigo=("community_cinco_aprovadas"),
            evento_gamificacao=("mission_reward_" "community_cinco_aprovadas"),
            xp=50,
        ),
        PoliticaRecompensaMissao(
            missao_codigo=("community_dez_aprovadas"),
            evento_gamificacao=("mission_reward_" "community_dez_aprovadas"),
            xp=100,
        ),
    )

    return CatalogoMissoesProducao(
        ruleset=ruleset,
        recompensas=recompensas,
        politica_instancia=INSTANCE_POLICY,
        instancia_chave=INSTANCE_KEY,
        origem_evento=(COMMUNITY_APPROVED_ORIGIN),
    )


def criar_ruleset_missoes_producao_v1() -> ConjuntoRegrasMissoes:
    return criar_catalogo_missoes_producao_v1().ruleset
