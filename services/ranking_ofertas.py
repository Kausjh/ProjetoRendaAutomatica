from __future__ import annotations

from models.oferta import Oferta
from services.historico_precos_service import ResultadoHistoricoPreco


class RankingOfertas:
    """
    Ordena ofertas utilizando todos os sinais disponíveis.

    Ordem de prioridade:

    1. Nota final
    2. Menor preço histórico
    3. Queda de preço
    4. Desconto
    5. Relevância do nicho
    6. Nota comercial
    7. Menor preço (desempate)
    """

    def ordenar(
        self,
        ofertas: list[
            tuple[
                Oferta,
                float,
                ResultadoHistoricoPreco | None,
                bool,
            ]
        ],
    ) -> list[
        tuple[
            Oferta,
            float,
            ResultadoHistoricoPreco | None,
            bool,
        ]
    ]:
        return sorted(
            ofertas,
            key=self._chave,
            reverse=True,
        )

    def _chave(
        self,
        item: tuple[
            Oferta,
            float,
            ResultadoHistoricoPreco | None,
            bool,
        ],
    ) -> tuple:
        oferta, nota, historico, republicada = item

        menor_preco = (
            historico is not None
            and historico.menor_preco_historico
            and not historico.primeiro_registro
        )

        queda = (
            abs(historico.variacao_percentual)
            if historico is not None and historico.preco_caiu
            else 0.0
        )

        return (
            nota,
            int(menor_preco),
            queda,
            oferta.desconto_percentual,
            oferta.relevancia_nicho,
            getattr(oferta, "nota_comercial", 0.0),
            -oferta.preco,
            int(republicada),
        )
