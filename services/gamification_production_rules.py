from __future__ import annotations

from dataclasses import dataclass

from services.gamification_rules import (
    ConjuntoRegrasGamificacao,
    RegraGamificacao,
)

VERSAO_RULESET_PRODUCAO_V1 = "gamification-reputation-production-v1"

NIVEIS_XP_PRODUCAO_V1 = (
    0,
    100,
    250,
    450,
    700,
    1000,
    1400,
    1900,
    2500,
    3200,
)

ESCOPOS_IDEMPOTENCIA_VALIDOS = frozenset(
    {
        "account_lifetime",
        "account_canonical_key_lifetime",
    }
)


@dataclass(frozen=True, slots=True)
class PoliticaEventoProducao:
    tipo_evento: str
    descricao: str
    xp_delta: int
    reputacao_delta: int
    escopo_idempotencia: str
    limite_por_janela: int | None = None
    janela_segundos: int | None = None

    def __post_init__(self) -> None:
        if not self.tipo_evento.strip():
            raise ValueError("tipo_evento nao pode ser vazio.")

        if not self.descricao.strip():
            raise ValueError("descricao nao pode ser vazia.")

        if self.xp_delta <= 0:
            raise ValueError("Eventos de producao V1 " "precisam conceder XP positivo.")

        if self.reputacao_delta != 0:
            raise ValueError("Reputacao comunitaria fica " "reservada para a Etapa 8.")

        if self.escopo_idempotencia not in ESCOPOS_IDEMPOTENCIA_VALIDOS:
            raise ValueError("Escopo de idempotencia invalido.")

        limite = self.limite_por_janela is not None

        janela = self.janela_segundos is not None

        if limite != janela:
            raise ValueError("Limite e janela precisam " "ser definidos juntos.")

    def como_regra_core(
        self,
    ) -> RegraGamificacao:
        return RegraGamificacao(
            tipo_evento=self.tipo_evento,
            xp_delta=self.xp_delta,
            reputacao_delta=(self.reputacao_delta),
            limite_por_janela=(self.limite_por_janela),
            janela_segundos=(self.janela_segundos),
        )


POLITICAS_EVENTOS_PRODUCAO_V1 = (
    PoliticaEventoProducao(
        tipo_evento=("onboarding_conta_criada"),
        descricao=("Conta criada e apta a usar " "o Radar."),
        xp_delta=40,
        reputacao_delta=0,
        escopo_idempotencia=("account_lifetime"),
    ),
    PoliticaEventoProducao(
        tipo_evento=("onboarding_dispositivo_vinculado"),
        descricao=("Primeiro dispositivo " "vinculado a conta."),
        xp_delta=20,
        reputacao_delta=0,
        escopo_idempotencia=("account_lifetime"),
    ),
    PoliticaEventoProducao(
        tipo_evento=("onboarding_preferencias_definidas"),
        descricao=("Preferencias iniciais " "configuradas."),
        xp_delta=20,
        reputacao_delta=0,
        escopo_idempotencia=("account_lifetime"),
    ),
    PoliticaEventoProducao(
        tipo_evento=("watchlist_produto_adicionado"),
        descricao=("Produto distinto adicionado " "a Lista pela primeira vez."),
        xp_delta=20,
        reputacao_delta=0,
        escopo_idempotencia=("account_canonical_key_lifetime"),
        limite_por_janela=10,
        janela_segundos=86400,
    ),
    PoliticaEventoProducao(
        tipo_evento=("watchlist_preco_alvo_definido"),
        descricao=("Preco-alvo definido pela " "primeira vez para um produto."),
        xp_delta=10,
        reputacao_delta=0,
        escopo_idempotencia=("account_canonical_key_lifetime"),
        limite_por_janela=10,
        janela_segundos=86400,
    ),
)


def obter_politica_producao_v1(
    tipo_evento: str,
) -> PoliticaEventoProducao | None:
    tipo = str(tipo_evento or "").strip()

    for politica in POLITICAS_EVENTOS_PRODUCAO_V1:
        if politica.tipo_evento == tipo:
            return politica

    return None


def criar_ruleset_producao_v1() -> ConjuntoRegrasGamificacao:
    return ConjuntoRegrasGamificacao(
        versao=(VERSAO_RULESET_PRODUCAO_V1),
        regras=tuple(politica.como_regra_core() for politica in POLITICAS_EVENTOS_PRODUCAO_V1),
        niveis_xp=(NIVEIS_XP_PRODUCAO_V1),
    )
