from __future__ import annotations

import json
from collections.abc import Mapping
from numbers import Real
from typing import Any
from urllib.parse import urlparse

import httpx

from models.inteligencia_ai import (
    RespostaProvedorInteligenciaAI,
    SolicitacaoInteligenciaAI,
)
from models.observabilidade_ai import UsoInteligenciaAI

SCHEMA_VERSION = 1

TIMEOUT_SEGUNDOS_PADRAO = 10.0

LIMITE_REQUISICAO_BYTES_PADRAO = 128 * 1024

LIMITE_RESPOSTA_BYTES_PADRAO = 64 * 1024

HOSTS_HTTP_LOCAIS = {
    "localhost",
    "127.0.0.1",
    "::1",
}


class ErroProvedorHttpInteligenciaAI(RuntimeError):
    pass


class ErroTransporteProvedorHttpInteligenciaAI(ErroProvedorHttpInteligenciaAI):
    pass


class TimeoutProvedorHttpInteligenciaAI(ErroProvedorHttpInteligenciaAI):
    pass


class ContratoProvedorHttpInteligenciaAIInvalido(ErroProvedorHttpInteligenciaAI):
    pass


class LimitePayloadProvedorHttpInteligenciaAIExcedido(ErroProvedorHttpInteligenciaAI):
    pass


class ProvedorHttpInteligenciaAI:
    """Adapter HTTP para um endpoint normalizado de IA.

    O endpoint nao precisa pertencer a nenhum fornecedor especifico.
    Ele apenas precisa implementar o contrato JSON deste projeto.

    Nenhuma decisao operacional e tomada aqui.
    """

    def __init__(
        self,
        *,
        endpoint: str,
        provedor: str,
        modelo: str | None = None,
        timeout_segundos: float = TIMEOUT_SEGUNDOS_PADRAO,
        limite_requisicao_bytes: int = LIMITE_REQUISICAO_BYTES_PADRAO,
        limite_resposta_bytes: int = LIMITE_RESPOSTA_BYTES_PADRAO,
        cabecalhos: Mapping[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.endpoint = _validar_endpoint(endpoint)

        self.provedor = _validar_texto_obrigatorio(
            provedor,
            campo="provedor",
        )

        self.modelo = _normalizar_texto_opcional(modelo)

        self.timeout_segundos = _validar_numero_positivo(
            timeout_segundos,
            campo="timeout_segundos",
        )

        self.limite_requisicao_bytes = _validar_inteiro_positivo(
            limite_requisicao_bytes,
            campo="limite_requisicao_bytes",
        )

        self.limite_resposta_bytes = _validar_inteiro_positivo(
            limite_resposta_bytes,
            campo="limite_resposta_bytes",
        )

        self.cabecalhos = _normalizar_cabecalhos(cabecalhos)

        self.transport = transport

    def interpretar(
        self,
        solicitacao: SolicitacaoInteligenciaAI,
    ) -> RespostaProvedorInteligenciaAI:
        if not isinstance(
            solicitacao,
            SolicitacaoInteligenciaAI,
        ):
            raise TypeError("solicitacao deve ser " "SolicitacaoInteligenciaAI")

        corpo = self._serializar_requisicao(solicitacao)

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            **self.cabecalhos,
        }

        timeout = httpx.Timeout(self.timeout_segundos)

        try:
            with httpx.Client(
                timeout=timeout,
                follow_redirects=False,
                transport=self.transport,
            ) as client:
                with client.stream(
                    "POST",
                    self.endpoint,
                    content=corpo,
                    headers=headers,
                ) as response:
                    return self._interpretar_response(response)

        except httpx.TimeoutException as erro:
            raise TimeoutProvedorHttpInteligenciaAI("timeout na chamada do provedor HTTP") from erro

        except httpx.RequestError as erro:
            raise ErroTransporteProvedorHttpInteligenciaAI(
                "erro de transporte na chamada do provedor HTTP"
            ) from erro

    def _serializar_requisicao(
        self,
        solicitacao: SolicitacaoInteligenciaAI,
    ) -> bytes:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "tarefa": solicitacao.tarefa,
            "contexto": dict(solicitacao.contexto),
            "modelo": self.modelo,
        }

        try:
            corpo = json.dumps(
                payload,
                ensure_ascii=False,
                separators=(
                    ",",
                    ":",
                ),
            ).encode("utf-8")
        except (
            TypeError,
            ValueError,
        ) as erro:
            raise ContratoProvedorHttpInteligenciaAIInvalido(
                "solicitacao nao e serializavel como JSON"
            ) from erro

        if len(corpo) > self.limite_requisicao_bytes:
            raise LimitePayloadProvedorHttpInteligenciaAIExcedido(
                "requisicao excede o limite de bytes"
            )

        return corpo

    def _interpretar_response(
        self,
        response: httpx.Response,
    ) -> RespostaProvedorInteligenciaAI:
        if response.status_code < 200 or response.status_code >= 300:
            raise ErroProvedorHttpInteligenciaAI(
                "provedor HTTP retornou status " f"{response.status_code}"
            )

        content_type = (
            response.headers.get(
                "content-type",
                "",
            )
            .split(
                ";",
                1,
            )[0]
            .strip()
            .casefold()
        )

        if content_type != "application/json":
            raise ContratoProvedorHttpInteligenciaAIInvalido(
                "provedor HTTP precisa retornar application/json"
            )

        partes: list[bytes] = []

        total = 0

        for parte in response.iter_bytes():
            total += len(parte)

            if total > self.limite_resposta_bytes:
                raise LimitePayloadProvedorHttpInteligenciaAIExcedido(
                    "resposta excede o limite de bytes"
                )

            partes.append(parte)

        corpo = b"".join(partes)

        try:
            texto = corpo.decode(
                "utf-8",
                errors="strict",
            )
        except UnicodeDecodeError as erro:
            raise ContratoProvedorHttpInteligenciaAIInvalido(
                "resposta nao possui UTF-8 valido"
            ) from erro

        try:
            dados = json.loads(texto)
        except json.JSONDecodeError as erro:
            raise ContratoProvedorHttpInteligenciaAIInvalido(
                "resposta nao possui JSON valido"
            ) from erro

        return self._converter_resposta(dados)

    def _converter_resposta(
        self,
        dados: Any,
    ) -> RespostaProvedorInteligenciaAI:
        if not isinstance(
            dados,
            dict,
        ):
            raise ContratoProvedorHttpInteligenciaAIInvalido(
                "raiz da resposta precisa ser objeto JSON"
            )

        campos_obrigatorios = {
            "schema_version",
            "conteudo",
            "confianca",
        }

        campos_opcionais = {
            "uso",
        }

        campos_recebidos = set(dados)

        campos_ausentes = campos_obrigatorios - campos_recebidos

        campos_desconhecidos = campos_recebidos - campos_obrigatorios - campos_opcionais

        if campos_ausentes or campos_desconhecidos:
            raise ContratoProvedorHttpInteligenciaAIInvalido(
                "campos da resposta nao correspondem " "ao contrato esperado"
            )

        if dados["schema_version"] != SCHEMA_VERSION:
            raise ContratoProvedorHttpInteligenciaAIInvalido(
                "schema_version da resposta nao suportado"
            )

        conteudo = dados["conteudo"]

        if not isinstance(
            conteudo,
            dict,
        ):
            raise ContratoProvedorHttpInteligenciaAIInvalido("conteudo precisa ser objeto JSON")

        confianca = dados["confianca"]

        if not isinstance(
            confianca,
            Real,
        ) or isinstance(
            confianca,
            bool,
        ):
            raise ContratoProvedorHttpInteligenciaAIInvalido("confianca precisa ser numerica")

        confianca_float = float(confianca)

        if not 0.0 <= confianca_float <= 1.0:
            raise ContratoProvedorHttpInteligenciaAIInvalido("confianca precisa ficar entre 0 e 1")

        uso = self._converter_uso(dados.get("uso"))

        return RespostaProvedorInteligenciaAI(
            conteudo=conteudo,
            confianca=confianca_float,
            provedor=self.provedor,
            modelo=self.modelo,
            uso=uso,
        )

    @staticmethod
    def _converter_uso(
        dados: Any,
    ) -> UsoInteligenciaAI | None:
        if dados is None:
            return None

        if not isinstance(
            dados,
            dict,
        ):
            raise ContratoProvedorHttpInteligenciaAIInvalido("uso precisa ser objeto JSON ou null")

        campos_permitidos = {
            "tokens_entrada",
            "tokens_saida",
            "tokens_total",
            "custo_estimado_usd",
        }

        desconhecidos = set(dados) - campos_permitidos

        if desconhecidos:
            raise ContratoProvedorHttpInteligenciaAIInvalido("uso possui campos nao suportados")

        try:
            return UsoInteligenciaAI(
                tokens_entrada=dados.get("tokens_entrada"),
                tokens_saida=dados.get("tokens_saida"),
                tokens_total=dados.get("tokens_total"),
                custo_estimado_usd=dados.get("custo_estimado_usd"),
            )

        except (
            TypeError,
            ValueError,
        ) as erro:
            raise ContratoProvedorHttpInteligenciaAIInvalido(
                "uso possui valores invalidos"
            ) from erro


def criar_provedor_http_inteligencia_ai(
    *,
    endpoint: str | None,
    provedor: str | None,
    modelo: str | None = None,
    auth_header_nome: str | None = None,
    auth_header_valor: str | None = None,
) -> ProvedorHttpInteligenciaAI | None:
    # Esta factory apenas faz wiring/configuracao.
    # Nenhuma chamada HTTP acontece durante a criacao.
    endpoint_normalizado = _normalizar_texto_opcional(endpoint)
    provedor_normalizado = _normalizar_texto_opcional(provedor)
    modelo_normalizado = _normalizar_texto_opcional(modelo)
    auth_nome_normalizado = _normalizar_texto_opcional(auth_header_nome)
    auth_valor_normalizado = _normalizar_texto_opcional(auth_header_valor)

    outros_campos = (
        provedor_normalizado,
        modelo_normalizado,
        auth_nome_normalizado,
        auth_valor_normalizado,
    )

    if endpoint_normalizado is None:
        if any(valor is not None for valor in outros_campos):
            raise ValueError(
                "endpoint precisa ser informado quando "
                "outra configuracao do provedor estiver definida"
            )

        return None

    if provedor_normalizado is None:
        raise ValueError("provedor precisa ser informado quando endpoint estiver definido")

    if (auth_nome_normalizado is None) != (auth_valor_normalizado is None):
        raise ValueError(
            "nome e valor do cabecalho de autenticacao " "precisam ser informados juntos"
        )

    cabecalhos = None

    if auth_nome_normalizado is not None:
        cabecalhos = {
            auth_nome_normalizado: auth_valor_normalizado,
        }

    return ProvedorHttpInteligenciaAI(
        endpoint=endpoint_normalizado,
        provedor=provedor_normalizado,
        modelo=modelo_normalizado,
        cabecalhos=cabecalhos,
    )


def _validar_endpoint(
    valor: str,
) -> str:
    endpoint = _validar_texto_obrigatorio(
        valor,
        campo="endpoint",
    )

    parsed = urlparse(endpoint)

    if parsed.scheme not in {
        "http",
        "https",
    }:
        raise ValueError("endpoint precisa usar http ou https")

    if not parsed.hostname:
        raise ValueError("endpoint precisa possuir host")

    if parsed.username is not None or parsed.password is not None:
        raise ValueError("credenciais nao podem ficar na URL")

    if parsed.fragment:
        raise ValueError("endpoint nao pode possuir fragmento")

    if parsed.scheme == "http" and parsed.hostname.casefold() not in HOSTS_HTTP_LOCAIS:
        raise ValueError("HTTP sem TLS so e permitido em localhost")

    return endpoint


def _normalizar_cabecalhos(
    valores: Mapping[str, str] | None,
) -> dict[str, str]:
    if valores is None:
        return {}

    if not isinstance(
        valores,
        Mapping,
    ):
        raise TypeError("cabecalhos precisa ser um Mapping")

    resultado: dict[
        str,
        str,
    ] = {}

    reservados = {
        "accept",
        "content-type",
    }

    for chave, valor in valores.items():
        nome = str(chave or "").strip()

        conteudo = str(valor or "").strip()

        if not nome:
            raise ValueError("nome de cabecalho nao pode ser vazio")

        if not conteudo:
            raise ValueError("valor de cabecalho nao pode ser vazio")

        if nome.casefold() in reservados:
            raise ValueError("Accept e Content-Type sao controlados " "pelo adapter")

        resultado[nome] = conteudo

    return resultado


def _validar_texto_obrigatorio(
    valor: object,
    *,
    campo: str,
) -> str:
    texto = str(valor or "").strip()

    if not texto:
        raise ValueError(f"{campo} precisa ser informado")

    return texto


def _normalizar_texto_opcional(
    valor: object,
) -> str | None:
    if valor is None:
        return None

    texto = str(valor).strip()

    return texto or None


def _validar_numero_positivo(
    valor: object,
    *,
    campo: str,
) -> float:
    try:
        numero = float(valor)
    except (
        TypeError,
        ValueError,
    ) as erro:
        raise ValueError(f"{campo} precisa ser numerico") from erro

    if numero <= 0:
        raise ValueError(f"{campo} precisa ser positivo")

    return numero


def _validar_inteiro_positivo(
    valor: object,
    *,
    campo: str,
) -> int:
    if (
        not isinstance(
            valor,
            int,
        )
        or isinstance(
            valor,
            bool,
        )
        or valor <= 0
    ):
        raise ValueError(f"{campo} precisa ser inteiro positivo")

    return valor
