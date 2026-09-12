from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from models.inteligencia_ai import (
    ResultadoInteligenciaAssistivaAI,
    SolicitacaoInteligenciaAI,
)
from models.oferta import Oferta
from services.classificador_produto import (
    ClassificadorProduto,
    ResultadoClassificacaoProduto,
)
from services.inteligencia_assistiva_ai import (
    CONFIANCA_MINIMA_PADRAO,
    ProvedorInteligenciaAI,
    interpretar_com_inteligencia_assistiva,
)


@dataclass(
    frozen=True,
    slots=True,
)
class CandidatoCategoriaProduto:
    categoria: str
    termos: tuple[str, ...]
    quantidade_termos: int


@dataclass(
    frozen=True,
    slots=True,
)
class DiagnosticoAmbiguidadeProduto:
    ambiguo: bool
    motivo: str
    identidade_principal_explicita: bool
    candidatos: tuple[
        CandidatoCategoriaProduto,
        ...,
    ]
    categorias_topo: tuple[
        str,
        ...,
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class ResultadoClassificacaoProdutoAssistidaAI:
    classificacao_final: ResultadoClassificacaoProduto
    classificacao_deterministica: ResultadoClassificacaoProduto
    diagnostico: DiagnosticoAmbiguidadeProduto
    inteligencia_ai: ResultadoInteligenciaAssistivaAI | None
    gate_ai_acionado: bool

    @property
    def eh_nicho(self) -> bool:
        return self.classificacao_final.eh_nicho

    @property
    def categoria(self) -> str | None:
        return self.classificacao_final.categoria

    @property
    def relevancia(self) -> float:
        return self.classificacao_final.relevancia

    @property
    def termos_encontrados(self) -> list[str]:
        return self.classificacao_final.termos_encontrados

    @property
    def motivo(self) -> str:
        return self.classificacao_final.motivo


class ClassificadorProdutoAssistidoAI:
    """Desambigua apenas classificacoes deterministicamente empatadas.

    A IA:
    - nunca transforma produto fora do nicho em produto do nicho;
    - nunca cria categoria nova;
    - nunca muda relevancia;
    - nunca sobrepoe identidade principal explicita;
    - nunca e chamada quando uma categoria vence deterministicamente.
    """

    def __init__(
        self,
        *,
        classificador: ClassificadorProduto | None = None,
        habilitado: bool = False,
        provedor: ProvedorInteligenciaAI | None = None,
        confianca_minima: float = CONFIANCA_MINIMA_PADRAO,
    ) -> None:
        self.classificador = classificador if classificador is not None else ClassificadorProduto()

        self.habilitado = bool(habilitado)

        self.provedor = provedor

        self.confianca_minima = confianca_minima

    def classificar(
        self,
        oferta: Oferta,
    ) -> ResultadoClassificacaoProdutoAssistidaAI:
        classificacao = self.classificador.classificar(oferta)

        diagnostico = self.diagnosticar_ambiguidade(
            oferta=oferta,
            classificacao=classificacao,
        )

        if not diagnostico.ambiguo:
            return ResultadoClassificacaoProdutoAssistidaAI(
                classificacao_final=classificacao,
                classificacao_deterministica=classificacao,
                diagnostico=diagnostico,
                inteligencia_ai=None,
                gate_ai_acionado=False,
            )

        fallback = {
            "categoria_sugerida": classificacao.categoria,
        }

        solicitacao = SolicitacaoInteligenciaAI(
            tarefa="desambiguar_categoria_produto",
            contexto=self._criar_contexto_ai(
                oferta=oferta,
                classificacao=classificacao,
                diagnostico=diagnostico,
            ),
        )

        resultado_ai = interpretar_com_inteligencia_assistiva(
            solicitacao=solicitacao,
            fallback=fallback,
            habilitado=self.habilitado,
            provedor=self.provedor,
            validador=lambda sugestao: (
                self._validar_sugestao_ai(
                    sugestao=sugestao,
                    diagnostico=diagnostico,
                )
            ),
            confianca_minima=self.confianca_minima,
        )

        classificacao_final = classificacao

        if resultado_ai.status == "sugestao_ai_validada" and resultado_ai.fallback_usado is False:
            categoria_sugerida = str(resultado_ai.sugestao["categoria_sugerida"]).strip()

            classificacao_final = self._aplicar_categoria_ai_validada(
                classificacao=classificacao,
                categoria_sugerida=categoria_sugerida,
            )

        return ResultadoClassificacaoProdutoAssistidaAI(
            classificacao_final=classificacao_final,
            classificacao_deterministica=classificacao,
            diagnostico=diagnostico,
            inteligencia_ai=resultado_ai,
            gate_ai_acionado=True,
        )

    def aplicar_classificacao(
        self,
        oferta: Oferta,
    ) -> ResultadoClassificacaoProdutoAssistidaAI:
        resultado = self.classificar(oferta)

        classificacao = resultado.classificacao_final

        oferta.eh_nicho = classificacao.eh_nicho

        oferta.categoria = classificacao.categoria

        oferta.relevancia_nicho = classificacao.relevancia

        oferta.termos_nicho = list(classificacao.termos_encontrados)

        oferta.motivo_classificacao = classificacao.motivo

        return resultado

    def diagnosticar_ambiguidade(
        self,
        *,
        oferta: Oferta,
        classificacao: ResultadoClassificacaoProduto | None = None,
    ) -> DiagnosticoAmbiguidadeProduto:
        if classificacao is None:
            classificacao = self.classificador.classificar(oferta)

        if classificacao.eh_nicho is not True or classificacao.categoria is None:
            return DiagnosticoAmbiguidadeProduto(
                ambiguo=False,
                motivo=("fora_do_nicho_ou_" "categoria_nao_identificada"),
                identidade_principal_explicita=False,
                candidatos=(),
                categorias_topo=(),
            )

        texto = self.classificador._normalizar_texto(oferta.nome)

        (
            categoria_principal,
            _,
        ) = self.classificador._identificar_identidade_principal(texto)

        if categoria_principal is not None:
            return DiagnosticoAmbiguidadeProduto(
                ambiguo=False,
                motivo="identidade_principal_explicita",
                identidade_principal_explicita=True,
                candidatos=(),
                categorias_topo=(categoria_principal,),
            )

        candidatos = self._candidatos_por_termos(texto)

        if not candidatos:
            return DiagnosticoAmbiguidadeProduto(
                ambiguo=False,
                motivo="sem_candidatos_categoria",
                identidade_principal_explicita=False,
                candidatos=(),
                categorias_topo=(),
            )

        maior_quantidade = max(candidato.quantidade_termos for candidato in candidatos)

        categorias_topo = tuple(
            candidato.categoria
            for candidato in candidatos
            if candidato.quantidade_termos == maior_quantidade
        )

        categoria_deterministica = classificacao.categoria

        if categoria_deterministica not in categorias_topo:
            return DiagnosticoAmbiguidadeProduto(
                ambiguo=False,
                motivo=("resultado_deterministico_" "fora_do_topo_calculado"),
                identidade_principal_explicita=False,
                candidatos=candidatos,
                categorias_topo=categorias_topo,
            )

        if len(categorias_topo) < 2:
            return DiagnosticoAmbiguidadeProduto(
                ambiguo=False,
                motivo=("categoria_deterministica_" "sem_empate"),
                identidade_principal_explicita=False,
                candidatos=candidatos,
                categorias_topo=categorias_topo,
            )

        return DiagnosticoAmbiguidadeProduto(
            ambiguo=True,
            motivo="empate_real_categorias_topo",
            identidade_principal_explicita=False,
            candidatos=candidatos,
            categorias_topo=categorias_topo,
        )

    def _candidatos_por_termos(
        self,
        texto: str,
    ) -> tuple[
        CandidatoCategoriaProduto,
        ...,
    ]:
        candidatos: list[CandidatoCategoriaProduto] = []

        for (
            categoria,
            termos,
        ) in self.classificador.CATEGORIAS.items():
            encontrados = self.classificador._localizar_termos(
                texto,
                termos,
            )

            if not encontrados:
                continue

            candidatos.append(
                CandidatoCategoriaProduto(
                    categoria=categoria,
                    termos=tuple(encontrados),
                    quantidade_termos=len(encontrados),
                )
            )

        return tuple(candidatos)

    @staticmethod
    def _criar_contexto_ai(
        *,
        oferta: Oferta,
        classificacao: ResultadoClassificacaoProduto,
        diagnostico: DiagnosticoAmbiguidadeProduto,
    ) -> dict[str, Any]:
        termos_topo = {
            candidato.categoria: list(candidato.termos)
            for candidato in diagnostico.candidatos
            if candidato.categoria in diagnostico.categorias_topo
        }

        return {
            "titulo": oferta.nome,
            "categoria_deterministica": (classificacao.categoria),
            "categorias_candidatas": list(diagnostico.categorias_topo),
            "termos_por_categoria": termos_topo,
            "regra": ("escolher_exatamente_uma_" "categoria_candidata"),
        }

    @staticmethod
    def _validar_sugestao_ai(
        *,
        sugestao: Mapping[str, Any],
        diagnostico: DiagnosticoAmbiguidadeProduto,
    ) -> bool:
        if not isinstance(
            sugestao,
            Mapping,
        ):
            return False

        if set(sugestao.keys()) != {
            "categoria_sugerida",
        }:
            return False

        categoria = sugestao.get("categoria_sugerida")

        if not isinstance(
            categoria,
            str,
        ):
            return False

        categoria = categoria.strip()

        if not categoria:
            return False

        return categoria in diagnostico.categorias_topo

    @staticmethod
    def _aplicar_categoria_ai_validada(
        *,
        classificacao: ResultadoClassificacaoProduto,
        categoria_sugerida: str,
    ) -> ResultadoClassificacaoProduto:
        if categoria_sugerida == classificacao.categoria:
            return classificacao

        return ResultadoClassificacaoProduto(
            eh_nicho=classificacao.eh_nicho,
            categoria=categoria_sugerida,
            relevancia=classificacao.relevancia,
            termos_encontrados=list(classificacao.termos_encontrados),
            motivo=(
                classificacao.motivo
                + " Categoria desambiguada por "
                + "IA assistiva apos validacao "
                + "deterministica; relevancia "
                + "deterministica preservada."
            ),
        )
