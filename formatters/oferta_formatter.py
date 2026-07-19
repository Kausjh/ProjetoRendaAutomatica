from models.oferta import Oferta
from services.historico_precos_service import ResultadoHistoricoPreco


class OfertaFormatter:

    @staticmethod
    def formatar(
        oferta: Oferta,
        resultado_historico: ResultadoHistoricoPreco | None = None
    ) -> str:
        informacao_preco = OfertaFormatter._formatar_preco(
            oferta
        )

        informacao_historico = OfertaFormatter._formatar_historico(
            oferta=oferta,
            resultado_historico=resultado_historico
        )

        return f"""
━━━━━━━━━━━━━━━━━━

🔥 OFERTA IMPERDÍVEL

📦 {oferta.nome}

🏪 Loja: {oferta.loja}
{informacao_preco}{informacao_historico}
🔗 {oferta.link}

━━━━━━━━━━━━━━━━━━
"""

    @staticmethod
    def _formatar_preco(
        oferta: Oferta
    ) -> str:
        if (
            oferta.preco_antigo is not None
            and oferta.desconto_percentual > 0
        ):
            return f"""
💸 De: {oferta.moeda} {oferta.preco_antigo:.2f}

✅ Por: {oferta.moeda} {oferta.preco:.2f}

💰 Desconto: {oferta.desconto_percentual:.0f}%
"""

        return f"""
💰 Preço: {oferta.moeda} {oferta.preco:.2f}
"""

    @staticmethod
    def _formatar_historico(
        oferta: Oferta,
        resultado_historico: ResultadoHistoricoPreco | None
    ) -> str:
        if resultado_historico is None:
            return ""

        if resultado_historico.primeiro_registro:
            return ""

        if not (
            resultado_historico.preco_caiu
            or resultado_historico.preco_subiu
        ):
            return ""

        preco_anterior = resultado_historico.preco_anterior

        if preco_anterior is None:
            return ""

        if resultado_historico.preco_caiu:
            icone_variacao = "📉"
            descricao_variacao = "Preço caiu"
        else:
            icone_variacao = "📈"
            descricao_variacao = "Preço subiu"

        variacao_absoluta = abs(
            resultado_historico.variacao_percentual
        )

        informacao_menor_preco = ""

        if resultado_historico.menor_preco_historico:
            informacao_menor_preco = (
                "\n\n🏆 Novo menor preço registrado"
            )

        return f"""
{icone_variacao} Preço anterior: {oferta.moeda} {preco_anterior:.2f}

📊 {descricao_variacao}: {variacao_absoluta:.2f}%{informacao_menor_preco}
"""