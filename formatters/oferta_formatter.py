# 63.8738, -149.7525

from formatters.limpador_titulo import limpar_titulo
from models.oferta import Oferta
from services.historico_precos_service import ResultadoHistoricoPreco

# Abaixo deste número de verificações o histórico é curto demais
# para afirmar que o preço é o melhor de todos os tempos.
REGISTROS_PARA_HISTORICO_CONFIAVEL = 10


class OfertaFormatter:

    @staticmethod
    def formatar(
        oferta: Oferta,
        resultado_historico: ResultadoHistoricoPreco | None = None,
    ) -> str:
        partes: list[str] = [
            "━━━━━━━━━━━━━━━━━━",
            "",
            OfertaFormatter._formatar_cabecalho(oferta, resultado_historico),
            "",
            f"📦 {limpar_titulo(oferta.nome)}",
            "",
            f"🏪 Loja: {oferta.loja}",
            "",
            OfertaFormatter._formatar_preco(
                oferta=oferta,
                resultado_historico=resultado_historico,
            ),
        ]

        historico = OfertaFormatter._formatar_historico(
            oferta=oferta,
            resultado_historico=resultado_historico,
        )

        if historico:
            partes.extend(["", historico])

        detalhes = OfertaFormatter._formatar_detalhes(oferta)

        if detalhes:
            partes.extend(["", detalhes])

        aviso_anomalia = OfertaFormatter._formatar_aviso_anomalia(oferta)

        if aviso_anomalia:
            partes.extend(["", aviso_anomalia])

        partes.extend(
            [
                "",
                f"🔗 {oferta.link}",
                "",
                "━━━━━━━━━━━━━━━━━━",
            ]
        )

        return "\n".join(partes)

    @staticmethod
    def _formatar_cabecalho(
        oferta: Oferta,
        resultado_historico: ResultadoHistoricoPreco | None,
    ) -> str:
        if oferta.tipo_oportunidade == "possivel_preco_bugado":
            return "🚨 POSSÍVEL PREÇO BUGADO"

        if oferta.tipo_oportunidade == "anomalia_forte":
            return "⚡ PREÇO FORA DO PADRÃO"

        if resultado_historico is not None and resultado_historico.menor_preco_historico:
            if not resultado_historico.primeiro_registro:
                registros = resultado_historico.quantidade_registros

                if registros >= REGISTROS_PARA_HISTORICO_CONFIAVEL:
                    return "🏆 MENOR PREÇO QUE JÁ REGISTRAMOS"

                return "📉 MENOR PREÇO DESDE QUE ACOMPANHAMOS"

        return "🔥 OFERTA IMPERDÍVEL"

    @staticmethod
    def _formatar_preco(
        oferta: Oferta,
        resultado_historico: ResultadoHistoricoPreco | None = None,
    ) -> str:
        referencia = OfertaFormatter._obter_referencia_historica(
            resultado_historico,
        )

        if referencia is not None and referencia > oferta.preco:
            economia = referencia - oferta.preco

            queda_percentual = (economia / referencia) * 100

            return "\n".join(
                [
                    f"✅ Por: {oferta.moeda} {oferta.preco:.2f}",
                    f"📉 Antes: {oferta.moeda} {referencia:.2f} " f"(preço que registramos)",
                    f"💵 Economia real: {oferta.moeda} {economia:.2f} "
                    f"({queda_percentual:.1f}%)",
                ]
            )

        if oferta.preco_antigo is not None and oferta.preco_antigo > oferta.preco:
            economia = oferta.preco_antigo - oferta.preco

            linhas = [
                f"💸 De: {oferta.moeda} {oferta.preco_antigo:.2f}",
                f"✅ Por: {oferta.moeda} {oferta.preco:.2f}",
                f"💵 Economia: {oferta.moeda} {economia:.2f}",
            ]

            if oferta.desconto_percentual > 0:
                linhas.append(f"🏷️ Desconto: {oferta.desconto_percentual:.2f}%")

            return "\n".join(linhas)

        return f"💰 Preço: {oferta.moeda} {oferta.preco:.2f}"

    @staticmethod
    def _obter_referencia_historica(
        resultado_historico: ResultadoHistoricoPreco | None,
    ) -> float | None:
        """Maior preço confiável já registrado por nós para o produto.

        Preferimos o preço anterior quando ele é maior que o menor
        histórico, porque representa o valor praticado mais recente.
        """

        if resultado_historico is None:
            return None

        if resultado_historico.primeiro_registro:
            return None

        candidatos = [
            valor
            for valor in (
                resultado_historico.preco_anterior,
                resultado_historico.menor_preco_anterior,
            )
            if valor is not None
        ]

        if not candidatos:
            return None

        return max(candidatos)

    @staticmethod
    def _formatar_historico(
        oferta: Oferta,
        resultado_historico: ResultadoHistoricoPreco | None,
    ) -> str:
        if resultado_historico is None:
            return ""

        if resultado_historico.primeiro_registro:
            return ""

        if resultado_historico.preco_anterior is None:
            return ""

        linhas: list[str] = ["📊 Nosso histórico de preços:"]

        diferenca = abs(oferta.preco - resultado_historico.preco_anterior)

        if resultado_historico.preco_subiu:
            linhas.append(
                f"📈 Subiu {oferta.moeda} {diferenca:.2f} "
                f"({abs(resultado_historico.variacao_percentual):.1f}%) "
                f"desde a última verificação"
            )

        menor_anterior = resultado_historico.menor_preco_anterior

        if resultado_historico.menor_preco_historico:
            if menor_anterior is not None and menor_anterior > oferta.preco:
                # O "Antes" exibido no bloco de preço usa o maior entre
                # preco_anterior e menor_preco_anterior. Quando os dois são
                # iguais, o valor entre parênteses aqui repete o que já
                # apareceu no "Antes" — omitimos para não duplicar.
                repete_antes = (
                    resultado_historico.preco_anterior is not None
                    and resultado_historico.preco_anterior == menor_anterior
                )

                if repete_antes:
                    linhas.append("🥇 Mais barato que qualquer preço que registramos")
                else:
                    linhas.append(
                        f"🥇 Mais barato que qualquer preço que registramos "
                        f"(anterior: {oferta.moeda} {menor_anterior:.2f})"
                    )
            else:
                linhas.append("🥇 Mais barato que qualquer preço que registramos")

        elif menor_anterior is not None:
            linhas.append(f"🔻 Menor que registramos: {oferta.moeda} {menor_anterior:.2f}")

        registros = resultado_historico.quantidade_registros

        if registros >= 3:
            linhas.append(f"👀 Acompanhamos este produto há {registros} verificações")

        if registros < REGISTROS_PARA_HISTORICO_CONFIAVEL:
            linhas.append("ℹ️ Monitoramos há pouco tempo: pode ter sido menor antes")

        return "\n".join(linhas)

    @staticmethod
    def _formatar_detalhes(oferta: Oferta) -> str:
        linhas: list[str] = []

        if oferta.categoria:
            linhas.append(f"📦 Categoria: {oferta.categoria}")

        if oferta.marca:
            linhas.append(f"🏅 Marca: {oferta.marca.title()}")

        # Exibe apenas os pontos que dizem respeito ao comprador:
        # nicho (20) + desconto (30) + preço (15) + histórico (15) = 80.
        # Os 20 pontos de "potencial comercial" ficam fora porque
        # medem interesse do canal, não do comprador, e geravam
        # leitura errada do tipo "nota alta = produto bom".
        nota_comprador = oferta.nota_tecnica + oferta.nota_historica

        if nota_comprador > 0:
            linhas.append(
                f"⭐ Vale a pena? {nota_comprador:.0f}/80 • "
                f"{OfertaFormatter._descricao_nota(nota_comprador)}"
            )

        return "\n".join(linhas)

    @staticmethod
    def _formatar_aviso_anomalia(oferta: Oferta) -> str:
        if not oferta.anomalia_preco or not oferta.anomalia_publicavel:
            return ""

        return "\n".join(
            [
                (
                    "⚠️ Detectamos um preço muito fora do padrão do nosso "
                    f"histórico ({oferta.queda_anomala_percentual:.1f}% abaixo)."
                ),
                (
                    "🔎 Mesmo em marketplace legítimo, confira vendedor, "
                    "variação do produto e condições do anúncio antes de pagar."
                ),
                "⏱️ Se for erro de preço, a oferta pode desaparecer rapidamente.",
            ]
        )

    @staticmethod
    def _descricao_nota(nota: float) -> str:
        # Faixas recalibradas para a escala 0-80 (pontos do comprador).
        if nota >= 75:
            return "Oferta excepcional"

        if nota >= 70:
            return "Excelente oportunidade"

        if nota >= 60:
            return "Muito boa"

        if nota >= 50:
            return "Boa oportunidade"

        return "Oferta comum"
