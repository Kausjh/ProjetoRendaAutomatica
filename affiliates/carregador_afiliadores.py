import json
import os
import re
from pathlib import Path
from typing import Any

from affiliates.configuracao_afiliador import ConfiguracaoAfiliador

PADRAO_VARIAVEL_AMBIENTE = re.compile(r"^\$\{([A-Z0-9_]+)\}$")


class CarregadorAfiliadores:

    def __init__(self, caminho_arquivo: str) -> None:
        self.caminho_arquivo = Path(caminho_arquivo)

    def carregar(self) -> list[ConfiguracaoAfiliador]:
        dados = self._ler_arquivo()

        afiliadores_brutos = dados.get("afiliadores")

        if not isinstance(afiliadores_brutos, list):
            raise ValueError(
                "O arquivo de afiliadores precisa possuir " "uma lista chamada 'afiliadores'."
            )

        configuracoes: list[ConfiguracaoAfiliador] = []

        nomes_encontrados: set[str] = set()
        dominios_encontrados: dict[str, str] = {}

        for indice, afiliador_bruto in enumerate(afiliadores_brutos, start=1):
            if not isinstance(afiliador_bruto, dict):
                raise ValueError(
                    f"Afiliador na posição {indice}: " "a configuração precisa ser um objeto JSON."
                )

            dados_resolvidos = self._resolver_variaveis_no_dict(afiliador_bruto)

            configuracao = ConfiguracaoAfiliador.criar_de_dict(
                dados=dados_resolvidos, indice=indice
            )

            nome_normalizado = configuracao.nome.lower()

            if nome_normalizado in nomes_encontrados:
                raise ValueError(
                    "Existem afiliadores com nomes duplicados: " f"'{configuracao.nome}'."
                )

            nomes_encontrados.add(nome_normalizado)

            if configuracao.ativo:
                for dominio in configuracao.dominios:
                    afiliador_existente = dominios_encontrados.get(dominio)

                    if afiliador_existente is not None:
                        raise ValueError(
                            f"O domínio '{dominio}' aparece em "
                            "mais de um afiliador ativo: "
                            f"'{afiliador_existente}' e "
                            f"'{configuracao.nome}'."
                        )

                    dominios_encontrados[dominio] = configuracao.nome

            configuracoes.append(configuracao)

        configuracoes.sort(key=lambda configuracao: (configuracao.prioridade), reverse=True)

        return configuracoes

    def _ler_arquivo(self) -> dict[str, Any]:
        if not self.caminho_arquivo.exists():
            raise FileNotFoundError(
                "Arquivo de configuração de afiliadores " f"não encontrado: {self.caminho_arquivo}"
            )

        try:
            with self.caminho_arquivo.open(mode="r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo)

        except json.JSONDecodeError as erro:
            raise ValueError(
                "O arquivo de configuração de afiliadores "
                "possui JSON inválido. "
                f"Linha {erro.lineno}, coluna {erro.colno}: "
                f"{erro.msg}"
            ) from erro

        except OSError as erro:
            raise OSError(
                "Não foi possível ler o arquivo de " f"afiliadores: {self.caminho_arquivo}"
            ) from erro

        if not isinstance(dados, dict):
            raise ValueError("A raiz do arquivo de afiliadores precisa " "ser um objeto JSON.")

        return dados

    def _resolver_variaveis_no_dict(self, dados: dict[str, Any]) -> dict[str, Any]:
        return {chave: self._resolver_valor(valor) for chave, valor in dados.items()}

    def _resolver_valor(self, valor: Any) -> Any:
        if isinstance(valor, dict):
            return {chave: self._resolver_valor(item) for chave, item in valor.items()}

        if isinstance(valor, list):
            return [self._resolver_valor(item) for item in valor]

        if not isinstance(valor, str):
            return valor

        correspondencia = PADRAO_VARIAVEL_AMBIENTE.fullmatch(valor.strip())

        if correspondencia is None:
            return valor

        nome_variavel = correspondencia.group(1)

        valor_variavel = os.getenv(nome_variavel)

        if valor_variavel is None:
            raise ValueError(
                "A configuração de afiliadores utiliza a "
                f"variável '{nome_variavel}', mas ela não "
                "está definida no ambiente."
            )

        valor_normalizado = valor_variavel.strip()

        if not valor_normalizado:
            raise ValueError(f"A variável '{nome_variavel}' não pode " "ficar vazia.")

        return valor_normalizado
