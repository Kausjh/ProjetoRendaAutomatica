from dataclasses import dataclass, field
from typing import Any

# 63.8738, -149.7525


@dataclass(frozen=True)
class ConfiguracaoAfiliador:
    nome: str
    tipo: str
    ativo: bool
    prioridade: int
    dominios: list[str]
    parametros: dict[str, str] = field(default_factory=dict)

    @classmethod
    def criar_de_dict(
        cls,
        dados: dict[str, Any],
        indice: int,
    ) -> "ConfiguracaoAfiliador":
        contexto = f"Afiliador na posi??o {indice}"

        nome = dados.get("nome")

        if not isinstance(nome, str) or not nome.strip():
            raise ValueError(f"{contexto}: o campo 'nome' precisa ser " "uma string n?o vazia.")

        tipo = dados.get("tipo")

        if not isinstance(tipo, str) or not tipo.strip():
            raise ValueError(f"{contexto}: o campo 'tipo' precisa ser " "uma string n?o vazia.")

        tipo_normalizado = tipo.strip().lower()

        tipos_suportados = {
            "mercado_livre",
            "parametros",
            "shopee",
            "awin",
        }

        if tipo_normalizado not in tipos_suportados:
            raise ValueError(
                f"{contexto}: tipo de afiliador n?o suportado: "
                f"'{tipo_normalizado}'. "
                "Tipos dispon?veis: "
                f"{', '.join(sorted(tipos_suportados))}."
            )

        ativo = dados.get(
            "ativo",
            True,
        )

        if not isinstance(ativo, bool):
            raise ValueError(f"{contexto}: o campo 'ativo' precisa ser " "true ou false.")

        prioridade = dados.get(
            "prioridade",
            0,
        )

        if not isinstance(prioridade, int) or isinstance(prioridade, bool):
            raise ValueError(f"{contexto}: o campo 'prioridade' precisa " "ser um n?mero inteiro.")

        dominios_brutos = dados.get("dominios")

        if not isinstance(dominios_brutos, list) or not dominios_brutos:
            raise ValueError(
                f"{contexto}: o campo 'dominios' precisa ser "
                "uma lista com pelo menos um dom?nio."
            )

        dominios: list[str] = []

        for dominio in dominios_brutos:
            if not isinstance(dominio, str) or not dominio.strip():
                raise ValueError(
                    f"{contexto}: todos os dom?nios precisam " "ser strings n?o vazias."
                )

            dominio_normalizado = dominio.strip().lower()

            if "://" in dominio_normalizado:
                raise ValueError(
                    f"{contexto}: informe somente o dom?nio, " f"sem http ou https: '{dominio}'."
                )

            if "/" in dominio_normalizado:
                raise ValueError(
                    f"{contexto}: o dom?nio n?o pode possuir " f"caminhos: '{dominio}'."
                )

            dominios.append(dominio_normalizado)

        parametros_brutos = dados.get(
            "parametros",
            {},
        )

        if not isinstance(parametros_brutos, dict):
            raise ValueError(f"{contexto}: o campo 'parametros' precisa " "ser um objeto JSON.")

        parametros: dict[str, str] = {}

        for chave, valor in parametros_brutos.items():
            if not isinstance(chave, str) or not chave.strip():
                raise ValueError(f"{contexto}: cada par?metro precisa " "possuir uma chave v?lida.")

            if not isinstance(valor, str):
                raise ValueError(
                    f"{contexto}: o valor do par?metro " f"'{chave}' precisa ser uma string."
                )

            parametros[chave.strip()] = valor

        if tipo_normalizado == "parametros" and not parametros:
            raise ValueError(
                f"{contexto}: afiliadores do tipo "
                "'parametros' precisam possuir pelo menos "
                "um par?metro."
            )

        return cls(
            nome=nome.strip(),
            tipo=tipo_normalizado,
            ativo=ativo,
            prioridade=prioridade,
            dominios=dominios,
            parametros=parametros,
        )
