import os


class ConfiguracoesAfiliados:

    def __init__(
        self
    ) -> None:
        self.caminho_arquivo = self._ler_texto(
            nome_variavel="ARQUIVO_AFILIADORES",
            valor_padrao="config/afiliadores.json"
        )

    def _ler_texto(
        self,
        nome_variavel: str,
        valor_padrao: str
    ) -> str:
        valor = os.getenv(
            nome_variavel,
            valor_padrao
        )

        valor_normalizado = (
            valor.strip()
        )

        if not valor_normalizado:
            raise ValueError(
                f"A variável {nome_variavel} não pode "
                "ficar vazia."
            )

        return valor_normalizado