import json
import logging
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from models.oferta import Oferta


logger = logging.getLogger(__name__)


class HistoricoPrecosRepository:
    def __init__(
        self,
        caminho_arquivo: str = "database/historico_precos.json"
    ) -> None:
        self.caminho_arquivo = Path(
            caminho_arquivo
        )

        self.caminho_arquivo.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        if not self.caminho_arquivo.exists():
            self._salvar_dados(
                {}
            )

    def registrar_preco(
        self,
        oferta: Oferta
    ) -> bool:
        dados = self._carregar_dados()

        produto = dados.get(
            oferta.link
        )

        if produto is None:
            produto = {
                "nome": oferta.nome,
                "loja": oferta.loja,
                "moeda": oferta.moeda,
                "historico": []
            }

            dados[oferta.link] = produto

        produto["nome"] = oferta.nome
        produto["loja"] = oferta.loja
        produto["moeda"] = oferta.moeda

        historico = produto.get(
            "historico",
            []
        )

        if not isinstance(
            historico,
            list
        ):
            logger.warning(
                "Histórico inválido encontrado para '%s'. "
                "Um novo histórico será iniciado.",
                oferta.nome
            )

            historico = []

        produto["historico"] = historico

        if historico:
            ultimo_registro = historico[-1]

            ultimo_preco = ultimo_registro.get(
                "preco"
            )

            if ultimo_preco == oferta.preco:
                logger.debug(
                    "O preço de '%s' não mudou: %.2f %s.",
                    oferta.nome,
                    oferta.preco,
                    oferta.moeda
                )

                return False

        novo_registro = {
            "data_hora": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "preco": oferta.preco
        }

        historico.append(
            novo_registro
        )

        self._salvar_dados(
            dados
        )

        logger.info(
            "Preço registrado no histórico: %s | %s %.2f",
            oferta.nome,
            oferta.moeda,
            oferta.preco
        )

        return True

    def obter_historico(
        self,
        link: str
    ) -> list[dict[str, Any]]:
        dados = self._carregar_dados()

        produto = dados.get(
            link
        )

        if not isinstance(
            produto,
            dict
        ):
            return []

        historico = produto.get(
            "historico",
            []
        )

        if not isinstance(
            historico,
            list
        ):
            return []

        return deepcopy(
            historico
        )

    def obter_produto(
        self,
        link: str
    ) -> dict[str, Any] | None:
        dados = self._carregar_dados()

        produto = dados.get(
            link
        )

        if not isinstance(
            produto,
            dict
        ):
            return None

        return deepcopy(
            produto
        )

    def obter_todos(
        self
    ) -> dict[str, dict[str, Any]]:
        dados = self._carregar_dados()

        return deepcopy(
            dados
        )

    def _carregar_dados(
        self
    ) -> dict[str, dict[str, Any]]:
        try:
            with self.caminho_arquivo.open(
                mode="r",
                encoding="utf-8"
            ) as arquivo:
                conteudo = json.load(
                    arquivo
                )

        except FileNotFoundError:
            logger.warning(
                "O arquivo de histórico de preços não foi encontrado. "
                "Um novo arquivo será criado."
            )

            self._salvar_dados(
                {}
            )

            return {}

        except json.JSONDecodeError:
            logger.exception(
                "O arquivo de histórico de preços contém JSON inválido."
            )

            return {}

        except OSError:
            logger.exception(
                "Não foi possível ler o histórico de preços."
            )

            return {}

        if not isinstance(
            conteudo,
            dict
        ):
            logger.warning(
                "O arquivo de histórico de preços possui formato inválido."
            )

            return {}

        return conteudo

    def _salvar_dados(
        self,
        dados: dict[str, dict[str, Any]]
    ) -> None:
        caminho_temporario = self.caminho_arquivo.with_suffix(
            ".tmp"
        )

        try:
            with caminho_temporario.open(
                mode="w",
                encoding="utf-8"
            ) as arquivo:
                json.dump(
                    dados,
                    arquivo,
                    ensure_ascii=False,
                    indent=4
                )

            caminho_temporario.replace(
                self.caminho_arquivo
            )

        except OSError:
            logger.exception(
                "Não foi possível salvar o histórico de preços."
            )

            if caminho_temporario.exists():
                try:
                    caminho_temporario.unlink()

                except OSError:
                    logger.exception(
                        "Não foi possível remover o arquivo temporário "
                        "do histórico de preços."
                    )