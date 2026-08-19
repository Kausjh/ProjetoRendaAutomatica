# 63.8738, -149.7525

from formatters.limpador_titulo import limpar_titulo
from models.oferta import Oferta
from services.historico_precos_service import ResultadoHistoricoPreco


class OfertaFormatter:

    @staticmethod
    def formatar(
        oferta: Oferta,
        resultado_historico: ResultadoHistoricoPreco | None = None,
    ) -> str:
        partes: list[str] = [
            "━━━━━━━━━━━━━━━━━━",
            "",
            OfertaFormatter._formatar_cabecalho(resultado_historico),
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
        resultado_historico: ResultadoHistoricoPreco | None,
    ) -> str:
        if resultado_historico is not None and resultado_historico.menor_preco_historico:
            if not resultado_historico.primeiro_registro:
                return "🏆 MENOR PREÇO JÁ REGISTRADO"

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
                linhas.append(
                    f"🥇 Nunca esteve tão barato "
                    f"(recorde anterior: {oferta.moeda} {menor_anterior:.2f})"
                )
            else:
                linhas.append("🥇 Nunca esteve tão barato")

        elif menor_anterior is not None:
            linhas.append(f"🔻 Menor preço já visto: {oferta.moeda} {menor_anterior:.2f}")

        registros = resultado_historico.quantidade_registros

        if registros >= 3:
            linhas.append(f"👀 Acompanhamos este produto há {registros} verificações")

        return "\n".join(linhas)

    @staticmethod
    def _formatar_detalhes(oferta: Oferta) -> str:
        linhas: list[str] = []

        if oferta.categoria:
            linhas.append(f"📦 Categoria: {oferta.categoria}")

        if oferta.marca:
            linhas.append(f"🏅 Marca: {oferta.marca.title()}")

        if oferta.nota_final > 0:
            linhas.append(
                f"⭐ Nota: {oferta.nota_final:.0f}/100 • "
                f"{OfertaFormatter._descricao_nota(oferta.nota_final)}"
            )

        return "\n".join(linhas)

    @staticmethod
    def _descricao_nota(nota: float) -> str:
        if nota >= 95:
            return "Oferta excepcional"

        if nota >= 90:
            return "Excelente oportunidade"

        if nota >= 80:
            return "Muito boa"

        if nota >= 70:
            return "Boa oportunidade"

        return "Oferta comum"
