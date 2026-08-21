# 63.8738, -149.7525

"""Detecção conservadora de preços anômalos.

O detector NÃO afirma que uma oferta é legítima e NÃO chama toda queda
forte de "bug". Ele apenas compara o preço atual com o nosso histórico e
atribui uma confiança operacional usando sinais que já existem no projeto.

Anomalias extremas ou pouco confiáveis ficam retidas em vez de serem
publicadas automaticamente.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from models.oferta import Oferta
from services.historico_precos_service import ResultadoHistoricoPreco


@dataclass(frozen=True)
class ResultadoAnomaliaPreco:
    detectada: bool
    publicavel: bool
    tipo: str
    queda_percentual: float
    confianca: float
    motivos: tuple[str, ...]


class DetectorAnomaliaPreco:
    DOMINIOS_CONFIAVEIS = {
        "mercadolivre.com.br",
        "www.mercadolivre.com.br",
        "produto.mercadolivre.com.br",
    }

    TERMOS_DE_RISCO = {
        "usado",
        "usada",
        "recondicionado",
        "recondicionada",
        "refurbished",
        "sucata",
        "defeito",
        "com defeito",
        "sem funcionar",
        "para retirada de peças",
        "somente a caixa",
        "apenas a caixa",
        "somente caixa",
        "apenas caixa",
        "carcaça",
        "kit reparo",
        "kit de reparo",
        "peça de reposição",
    }

    def __init__(
        self,
        ativa: bool = True,
        queda_minima_anomalia: float = 45.0,
        queda_minima_preco_bugado: float = 55.0,
        queda_maxima_publicavel: float = 75.0,
        registros_minimos: int = 4,
        confianca_minima_publicacao: float = 75.0,
    ) -> None:
        self.ativa = ativa
        self.queda_minima_anomalia = queda_minima_anomalia
        self.queda_minima_preco_bugado = queda_minima_preco_bugado
        self.queda_maxima_publicavel = queda_maxima_publicavel
        self.registros_minimos = registros_minimos
        self.confianca_minima_publicacao = confianca_minima_publicacao

    def avaliar(
        self,
        oferta: Oferta,
        resultado_historico: ResultadoHistoricoPreco | None,
    ) -> ResultadoAnomaliaPreco:
        self._limpar_estado(oferta)

        if not self.ativa:
            return self._normal("Detector de anomalias desativado.")

        if resultado_historico is None or resultado_historico.primeiro_registro:
            return self._normal("Sem histórico suficiente para detectar anomalia.")

        queda = self._calcular_queda_relevante(
            oferta=oferta,
            resultado_historico=resultado_historico,
        )

        if queda < self.queda_minima_anomalia:
            return self._normal(f"Queda de {queda:.1f}% abaixo do limiar de anomalia.")

        motivos: list[str] = []
        confianca = 0.0

        registros = resultado_historico.quantidade_registros

        if registros >= self.registros_minimos:
            confianca += 25.0
            motivos.append(f"Histórico com {registros} verificações.")
        else:
            motivos.append(f"Histórico curto: somente {registros} verificações.")

        if oferta.id_produto or oferta.id_anuncio:
            confianca += 20.0
            motivos.append("Produto possui identificador do marketplace.")
        else:
            motivos.append("Produto sem identificador confiável do marketplace.")

        host = (urlparse(oferta.link).hostname or "").lower()

        if host in self.DOMINIOS_CONFIAVEIS:
            confianca += 15.0
            motivos.append("Link aponta para domínio oficial do Mercado Livre.")
        else:
            motivos.append("Domínio da oferta não está na lista confiável.")

        if resultado_historico.preco_caiu and resultado_historico.menor_preco_historico:
            confianca += 15.0
            motivos.append("Queda real e novo menor preço no nosso histórico.")
        elif resultado_historico.preco_caiu:
            confianca += 8.0
            motivos.append("Preço caiu em relação à última verificação.")

        if oferta.preco > 10:
            confianca += 10.0
        else:
            motivos.append("Preço absoluto muito baixo exige revisão.")

        riscos_titulo = self._encontrar_termos_de_risco(oferta.nome)

        if riscos_titulo:
            motivos.append("Título contém termo(s) de risco: " + ", ".join(riscos_titulo) + ".")
        else:
            confianca += 15.0
            motivos.append("Título sem sinais óbvios de usado/defeito/peça.")

        confianca = min(confianca, 100.0)

        if queda >= self.queda_maxima_publicavel:
            return self._aplicar_resultado(
                oferta=oferta,
                publicavel=False,
                tipo="anomalia_retida",
                queda=queda,
                confianca=confianca,
                motivos=motivos
                + [
                    (
                        f"Queda extrema de {queda:.1f}% ultrapassa o limite "
                        "de publicação automática."
                    )
                ],
            )

        if riscos_titulo:
            return self._aplicar_resultado(
                oferta=oferta,
                publicavel=False,
                tipo="anomalia_retida",
                queda=queda,
                confianca=confianca,
                motivos=motivos + ["Anomalia retida por sinais de risco no título."],
            )

        if registros < self.registros_minimos:
            return self._aplicar_resultado(
                oferta=oferta,
                publicavel=False,
                tipo="anomalia_retida",
                queda=queda,
                confianca=confianca,
                motivos=motivos + ["Anomalia retida por histórico insuficiente."],
            )

        if not (oferta.id_produto or oferta.id_anuncio):
            return self._aplicar_resultado(
                oferta=oferta,
                publicavel=False,
                tipo="anomalia_retida",
                queda=queda,
                confianca=confianca,
                motivos=motivos + ["Anomalia retida por falta de identificador do produto."],
            )

        if host not in self.DOMINIOS_CONFIAVEIS:
            return self._aplicar_resultado(
                oferta=oferta,
                publicavel=False,
                tipo="anomalia_retida",
                queda=queda,
                confianca=confianca,
                motivos=motivos + ["Anomalia retida por domínio não confiável."],
            )

        if confianca < self.confianca_minima_publicacao:
            return self._aplicar_resultado(
                oferta=oferta,
                publicavel=False,
                tipo="anomalia_retida",
                queda=queda,
                confianca=confianca,
                motivos=motivos
                + [
                    (
                        f"Confiança {confianca:.0f}/100 abaixo do mínimo "
                        f"{self.confianca_minima_publicacao:.0f}/100."
                    )
                ],
            )

        tipo = (
            "possivel_preco_bugado" if queda >= self.queda_minima_preco_bugado else "anomalia_forte"
        )

        return self._aplicar_resultado(
            oferta=oferta,
            publicavel=True,
            tipo=tipo,
            queda=queda,
            confianca=confianca,
            motivos=motivos,
        )

    def _calcular_queda_relevante(
        self,
        oferta: Oferta,
        resultado_historico: ResultadoHistoricoPreco,
    ) -> float:
        quedas: list[float] = []

        if (
            resultado_historico.preco_caiu
            and resultado_historico.preco_anterior is not None
            and resultado_historico.preco_anterior > 0
        ):
            quedas.append(abs(float(resultado_historico.variacao_percentual)))

        menor_anterior = resultado_historico.menor_preco_anterior

        if menor_anterior is not None and menor_anterior > oferta.preco and menor_anterior > 0:
            queda_vs_menor = ((menor_anterior - oferta.preco) / menor_anterior) * 100
            quedas.append(queda_vs_menor)

        if not quedas:
            return 0.0

        return round(max(quedas), 2)

    def _encontrar_termos_de_risco(self, titulo: str) -> list[str]:
        texto = titulo.casefold()

        return sorted(termo for termo in self.TERMOS_DE_RISCO if termo.casefold() in texto)

    def _normal(self, motivo: str) -> ResultadoAnomaliaPreco:
        return ResultadoAnomaliaPreco(
            detectada=False,
            publicavel=False,
            tipo="normal",
            queda_percentual=0.0,
            confianca=0.0,
            motivos=(motivo,),
        )

    def _aplicar_resultado(
        self,
        oferta: Oferta,
        publicavel: bool,
        tipo: str,
        queda: float,
        confianca: float,
        motivos: list[str],
    ) -> ResultadoAnomaliaPreco:
        oferta.anomalia_preco = True
        oferta.anomalia_publicavel = publicavel
        oferta.tipo_oportunidade = tipo
        oferta.confianca_anomalia = round(confianca, 2)
        oferta.queda_anomala_percentual = round(queda, 2)
        oferta.motivos_anomalia = list(motivos)

        return ResultadoAnomaliaPreco(
            detectada=True,
            publicavel=publicavel,
            tipo=tipo,
            queda_percentual=round(queda, 2),
            confianca=round(confianca, 2),
            motivos=tuple(motivos),
        )

    @staticmethod
    def _limpar_estado(oferta: Oferta) -> None:
        oferta.tipo_oportunidade = "normal"
        oferta.anomalia_preco = False
        oferta.anomalia_publicavel = False
        oferta.confianca_anomalia = 0.0
        oferta.queda_anomala_percentual = 0.0
        oferta.motivos_anomalia.clear()
