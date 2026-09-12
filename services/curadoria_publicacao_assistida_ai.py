from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from models.inteligencia_ai import (
    ResultadoInteligenciaAssistivaAI,
    SolicitacaoInteligenciaAI,
)
from models.oferta import Oferta
from services.controle_operacional_ai import ControleOperacionalInteligenciaAI
from services.curadoria_publicacao import (
    CuradoriaPublicacao,
    ResultadoCuradoriaPublicacao,
)
from services.inteligencia_assistiva_ai import (
    CONFIANCA_MINIMA_PADRAO,
    ProvedorInteligenciaAI,
    interpretar_com_inteligencia_assistiva,
)

ACAO_MANTER = "manter"
ACAO_REVISAO_MANUAL = "revisao_manual"

ACOES_CURADORIA_AI_PERMITIDAS = frozenset(
    {
        ACAO_MANTER,
        ACAO_REVISAO_MANUAL,
    }
)


@dataclass(
    frozen=True,
    slots=True,
)
class DiagnosticoGateCuradoriaAI:
    acionar_ai: bool
    motivo: str
    sinais: tuple[str, ...]


@dataclass(
    frozen=True,
    slots=True,
)
class ResultadoCuradoriaPublicacaoAssistidaAI:
    curadoria_final: ResultadoCuradoriaPublicacao
    curadoria_deterministica: ResultadoCuradoriaPublicacao
    diagnostico: DiagnosticoGateCuradoriaAI
    inteligencia_ai: ResultadoInteligenciaAssistivaAI | None
    gate_ai_acionado: bool
    revisao_manual_sugerida: bool

    @property
    def publicavel(self) -> bool:
        return self.curadoria_final.publicavel

    @property
    def nota(self) -> float:
        return self.curadoria_final.nota

    @property
    def motivos(self) -> tuple[str, ...]:
        return self.curadoria_final.motivos

    @property
    def bloqueios(self) -> tuple[str, ...]:
        return self.curadoria_final.bloqueios


class CuradoriaPublicacaoAssistidaAI:
    """Adiciona interpretacao assistiva sem alterar a curadoria base.

    A IA nunca:
    - transforma reprovacao em aprovacao;
    - transforma aprovacao em reprovacao;
    - altera nota;
    - remove ou adiciona bloqueio;
    - altera motivos deterministas;
    - autoriza publicacao;
    - altera budget, preco ou pontuacao.

    Sua unica saida aceita e uma sugestao informativa:
    manter a decisao deterministica ou recomendar revisao manual.
    """

    def __init__(
        self,
        *,
        curadoria: CuradoriaPublicacao | None = None,
        habilitado: bool = False,
        provedor: ProvedorInteligenciaAI | None = None,
        confianca_minima: float = CONFIANCA_MINIMA_PADRAO,
        controle_operacional: ControleOperacionalInteligenciaAI | None = None,
    ) -> None:
        self.curadoria = curadoria if curadoria is not None else CuradoriaPublicacao()

        self.habilitado = bool(habilitado)

        self.provedor = provedor
        self.confianca_minima = confianca_minima

        self.controle_operacional = controle_operacional

    def analisar(
        self,
        oferta: Oferta,
    ) -> ResultadoCuradoriaPublicacaoAssistidaAI:
        resultado_deterministico = self.curadoria.analisar(oferta)

        diagnostico = self.diagnosticar_gate(
            oferta=oferta,
            resultado=resultado_deterministico,
        )

        if not diagnostico.acionar_ai:
            return ResultadoCuradoriaPublicacaoAssistidaAI(
                curadoria_final=resultado_deterministico,
                curadoria_deterministica=resultado_deterministico,
                diagnostico=diagnostico,
                inteligencia_ai=None,
                gate_ai_acionado=False,
                revisao_manual_sugerida=False,
            )

        fallback = {
            "acao_sugerida": ACAO_MANTER,
            "motivo_curto": ("curadoria_deterministica_preservada"),
        }

        solicitacao = SolicitacaoInteligenciaAI(
            tarefa="interpretar_incerteza_editorial",
            contexto=self._criar_contexto_ai(
                oferta=oferta,
                diagnostico=diagnostico,
            ),
        )

        resultado_ai = interpretar_com_inteligencia_assistiva(
            solicitacao=solicitacao,
            fallback=fallback,
            habilitado=self.habilitado,
            provedor=self.provedor,
            validador=self._validar_sugestao_ai,
            confianca_minima=self.confianca_minima,
            controle_operacional=self.controle_operacional,
        )

        revisao_manual_sugerida = False

        if resultado_ai.status == "sugestao_ai_validada" and resultado_ai.fallback_usado is False:
            revisao_manual_sugerida = (
                resultado_ai.sugestao.get("acao_sugerida") == ACAO_REVISAO_MANUAL
            )

        return ResultadoCuradoriaPublicacaoAssistidaAI(
            curadoria_final=resultado_deterministico,
            curadoria_deterministica=resultado_deterministico,
            diagnostico=diagnostico,
            inteligencia_ai=resultado_ai,
            gate_ai_acionado=True,
            revisao_manual_sugerida=revisao_manual_sugerida,
        )

    def diagnosticar_gate(
        self,
        *,
        oferta: Oferta,
        resultado: ResultadoCuradoriaPublicacao | None = None,
    ) -> DiagnosticoGateCuradoriaAI:
        if resultado is None:
            resultado = self.curadoria.analisar(oferta)

        if resultado.publicavel is not True:
            return DiagnosticoGateCuradoriaAI(
                acionar_ai=False,
                motivo="reprovada_deterministicamente",
                sinais=(),
            )

        if resultado.bloqueios:
            return DiagnosticoGateCuradoriaAI(
                acionar_ai=False,
                motivo="possui_bloqueio_deterministico",
                sinais=(),
            )

        sinais: list[str] = []

        if oferta.relevancia_nicho < 80:
            sinais.append("relevancia_nicho_abaixo_de_80")

        if oferta.confianca_normalizacao < 90:
            sinais.append("confianca_normalizacao_abaixo_de_90")

        texto = self.curadoria._normalizar(oferta.nome)

        termos_kit = self.curadoria._encontrar(
            texto,
            self.curadoria.TERMOS_KIT_COMBO,
        )

        if termos_kit and oferta.categoria not in self.curadoria.CATEGORIAS_ONDE_KIT_E_NORMAL:
            sinais.append("kit_combo_fora_categoria_normal")

        if oferta.preco_antigo is not None and oferta.preco_antigo <= oferta.preco:
            sinais.append("preco_antigo_nao_confirma_desconto")

        if not sinais:
            return DiagnosticoGateCuradoriaAI(
                acionar_ai=False,
                motivo="sem_incerteza_editorial_objetiva",
                sinais=(),
            )

        return DiagnosticoGateCuradoriaAI(
            acionar_ai=True,
            motivo="incerteza_editorial_objetiva",
            sinais=tuple(sinais),
        )

    @staticmethod
    def _criar_contexto_ai(
        *,
        oferta: Oferta,
        diagnostico: DiagnosticoGateCuradoriaAI,
    ) -> dict[str, Any]:
        return {
            "titulo": oferta.nome,
            "categoria": oferta.categoria,
            "sinais_deterministicos": list(diagnostico.sinais),
            "acoes_permitidas": [
                ACAO_MANTER,
                ACAO_REVISAO_MANUAL,
            ],
            "regra": ("nao_alterar_decisao_deterministica"),
        }

    @staticmethod
    def _validar_sugestao_ai(
        sugestao: Mapping[str, Any],
    ) -> bool:
        if not isinstance(
            sugestao,
            Mapping,
        ):
            return False

        if set(sugestao.keys()) != {
            "acao_sugerida",
            "motivo_curto",
        }:
            return False

        acao = sugestao.get("acao_sugerida")

        motivo = sugestao.get("motivo_curto")

        if not isinstance(
            acao,
            str,
        ):
            return False

        if acao not in ACOES_CURADORIA_AI_PERMITIDAS:
            return False

        if not isinstance(
            motivo,
            str,
        ):
            return False

        motivo = motivo.strip()

        if not motivo:
            return False

        if len(motivo) > 240:
            return False

        return True
