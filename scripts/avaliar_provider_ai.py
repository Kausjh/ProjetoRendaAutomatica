from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from config.configuracoes import Configuracoes
from models.inteligencia_ai import SolicitacaoInteligenciaAI
from models.oferta import Oferta
from services.classificador_produto_assistido_ai import ClassificadorProdutoAssistidoAI
from services.controle_operacional_ai import (
    ControleOperacionalInteligenciaAI,
)
from services.curadoria_publicacao_assistida_ai import (
    ACAO_REVISAO_MANUAL,
    CuradoriaPublicacaoAssistidaAI,
)
from services.inteligencia_assistiva_ai import (
    interpretar_com_inteligencia_assistiva,
)
from services.provedor_http_inteligencia_ai import (
    ProvedorHttpInteligenciaAI,
    criar_provedor_http_inteligencia_ai,
)
from services.provedor_openai_responses_ai import (
    MODELO_OPENAI_PADRAO,
    ProvedorOpenAIResponsesAI,
)

TAREFA_AVALIACAO = "avaliar_provider_ai"
FALLBACK_AVALIACAO = {
    "resultado": "fallback_deterministico",
}
SUGESTAO_ESPERADA = {
    "resultado": "ok",
}


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=("Avalia o contrato operacional de um provider AI " "fora do pipeline normal.")
    )

    parser.add_argument(
        "--modo",
        choices=(
            "mock",
            "real",
        ),
        default="mock",
        help=("mock nao usa rede. real exige configuracao " "e --permitir-rede-real."),
    )

    parser.add_argument(
        "--permitir-rede-real",
        action="store_true",
        help=(
            "Autoriza somente este harness a tentar uma avaliacao "
            "real. O kill switch continua sendo respeitado."
        ),
    )

    parser.add_argument(
        "--provider-real",
        choices=(
            "generico",
            "openai",
        ),
        default="generico",
        help=("Seleciona o provider usado somente no caso contrato " "quando --modo real."),
    )

    parser.add_argument(
        "--caso",
        choices=(
            "contrato",
            "classificador",
            "curadoria",
            "dominios",
        ),
        default="contrato",
        help=(
            "contrato preserva o teste sintetico V20B. "
            "Os casos de dominio sao exclusivos do modo mock."
        ),
    )

    parser.add_argument(
        "--relatorio",
        type=Path,
        default=None,
        help=("Caminho do JSON de saida. Por padrao usa " "logs/reports."),
    )

    return parser


def _solicitacao_avaliacao() -> SolicitacaoInteligenciaAI:
    return SolicitacaoInteligenciaAI(
        tarefa=TAREFA_AVALIACAO,
        contexto={
            "entrada": "ping",
            "contrato": {
                "resultado_esperado": "ok",
                "somente_sugestao": True,
                "autoridade_operacional": False,
            },
        },
    )


def _validar_sugestao(
    sugestao: dict[str, Any],
) -> bool:
    return sugestao == SUGESTAO_ESPERADA


def _handler_mock(
    request: httpx.Request,
) -> httpx.Response:
    payload = json.loads(request.content.decode("utf-8"))

    if payload.get("schema_version") != 1:
        return httpx.Response(
            400,
            json={
                "erro": "schema_version",
            },
        )

    tarefa = payload.get("tarefa")

    if tarefa == TAREFA_AVALIACAO:
        conteudo = dict(SUGESTAO_ESPERADA)
    elif tarefa == "desambiguar_categoria_produto":
        conteudo = {
            "categoria_sugerida": "Armazenamento",
        }
    elif tarefa == "interpretar_incerteza_editorial":
        conteudo = {
            "acao_sugerida": ACAO_REVISAO_MANUAL,
            "motivo_curto": ("confianca de normalizacao baixa; " "revisao manual sugerida"),
        }
    else:
        return httpx.Response(
            400,
            json={
                "erro": "tarefa",
            },
        )

    return httpx.Response(
        200,
        headers={
            "Content-Type": "application/json",
        },
        json={
            "schema_version": 1,
            "conteudo": conteudo,
            "confianca": 0.99,
            "uso": {
                "tokens_entrada": 12,
                "tokens_saida": 4,
                "tokens_total": 16,
                "custo_estimado_usd": 0.0001,
            },
        },
    )


def _criar_provider_mock() -> ProvedorHttpInteligenciaAI:
    return ProvedorHttpInteligenciaAI(
        endpoint="http://127.0.0.1/v20b/mock",
        provedor="mock-v20b",
        modelo="mock-local",
        transport=httpx.MockTransport(_handler_mock),
    )


def _criar_controle_mock() -> ControleOperacionalInteligenciaAI:
    return ControleOperacionalInteligenciaAI(
        kill_switch_ativo=False,
        limite_chamadas_externas=1,
        limite_tokens_total=1000,
        limite_custo_estimado_usd=0.10,
    )


def _buscar_openai_api_key_harness() -> str:
    valor = os.getenv("OPENAI_API_KEY")

    if valor is None or not valor.strip():
        raise RuntimeError("OPENAI_API_KEY nao esta configurada no .env local.")

    return valor.strip()


def _buscar_openai_model_harness() -> str:
    valor = os.getenv("OPENAI_MODEL")

    if valor is None or not valor.strip():
        return MODELO_OPENAI_PADRAO

    return valor.strip()


def _criar_provider_openai_harness() -> ProvedorOpenAIResponsesAI:
    return ProvedorOpenAIResponsesAI(
        api_key=_buscar_openai_api_key_harness(),
        modelo=_buscar_openai_model_harness(),
    )


def _criar_provider_real(
    *,
    permitir_rede_real: bool,
    provider_real: str = "generico",
) -> tuple[
    Any,
    ControleOperacionalInteligenciaAI,
]:
    if not permitir_rede_real:
        raise RuntimeError("Modo real exige --permitir-rede-real.")

    if provider_real not in {
        "generico",
        "openai",
    }:
        raise ValueError("provider_real precisa ser generico ou openai")

    configuracoes = Configuracoes()

    if provider_real == "openai":
        provedor = _criar_provider_openai_harness()
    else:
        provedor = criar_provedor_http_inteligencia_ai(
            endpoint=configuracoes.ai_provedor_endpoint,
            provedor=configuracoes.ai_provedor_nome,
            modelo=configuracoes.ai_provedor_modelo,
            auth_header_nome=(configuracoes.ai_provedor_auth_header_nome),
            auth_header_valor=(configuracoes.ai_provedor_auth_header_valor),
        )

        if provedor is None:
            raise RuntimeError("Provider AI real nao esta configurado.")

    controle = ControleOperacionalInteligenciaAI(
        kill_switch_ativo=(configuracoes.ai_kill_switch_ativo),
        limite_chamadas_externas=1,
        limite_tokens_total=(configuracoes.ai_limite_tokens_total),
        limite_custo_estimado_usd=(configuracoes.ai_limite_custo_estimado_usd),
    )

    return (
        provedor,
        controle,
    )


def _caminho_relatorio_padrao() -> Path:
    agora = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")

    return Path("logs/reports") / ("avaliacao_provider_ai_" + agora + ".json")


def executar_avaliacao(
    *,
    modo: str = "mock",
    permitir_rede_real: bool = False,
    provider_real: str = "generico",
    caminho_relatorio: Path | None = None,
) -> dict[str, Any]:
    if modo not in {
        "mock",
        "real",
    }:
        raise ValueError("modo precisa ser mock ou real")

    if modo == "mock":
        provedor = _criar_provider_mock()
        controle = _criar_controle_mock()
    else:
        provedor, controle = _criar_provider_real(
            permitir_rede_real=(permitir_rede_real),
            provider_real=provider_real,
        )

    solicitacao = _solicitacao_avaliacao()

    resultado = interpretar_com_inteligencia_assistiva(
        solicitacao=solicitacao,
        fallback=FALLBACK_AVALIACAO,
        habilitado=True,
        provedor=provedor,
        validador=_validar_sugestao,
        controle_operacional=controle,
    )

    snapshot = controle.snapshot()

    relatorio: dict[str, Any] = {
        "schema_version": 1,
        "capturado_em": (datetime.now().astimezone().isoformat(timespec="seconds")),
        "modo": modo,
        "provider_real": (provider_real if modo == "real" else None),
        "tarefa": solicitacao.tarefa,
        "resultado": {
            "status": resultado.status,
            "origem": resultado.origem,
            "confianca": resultado.confianca,
            "provedor": resultado.provedor,
            "modelo": resultado.modelo,
            "fallback_usado": (resultado.fallback_usado),
            "validada_deterministicamente": (resultado.validada_deterministicamente),
            "somente_sugestao": (resultado.somente_sugestao),
            "autoriza_publicacao": (resultado.autoriza_publicacao),
            "autoriza_alteracao_budget": (resultado.autoriza_alteracao_budget),
            "substitui_regras_deterministicas": (resultado.substitui_regras_deterministicas),
            "tipo_erro": resultado.tipo_erro,
        },
        "controle_operacional": asdict(snapshot),
    }

    destino = caminho_relatorio if caminho_relatorio is not None else _caminho_relatorio_padrao()

    destino.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destino.write_text(
        json.dumps(
            relatorio,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    relatorio["caminho_relatorio"] = str(destino)

    return relatorio


def _resultado_ai_para_dict(
    resultado: Any,
) -> dict[str, Any] | None:
    if resultado is None:
        return None

    return {
        "status": resultado.status,
        "origem": resultado.origem,
        "confianca": resultado.confianca,
        "provedor": resultado.provedor,
        "modelo": resultado.modelo,
        "fallback_usado": resultado.fallback_usado,
        "validada_deterministicamente": (resultado.validada_deterministicamente),
        "somente_sugestao": resultado.somente_sugestao,
        "autoriza_publicacao": (resultado.autoriza_publicacao),
        "autoriza_alteracao_budget": (resultado.autoriza_alteracao_budget),
        "substitui_regras_deterministicas": (resultado.substitui_regras_deterministicas),
        "tipo_erro": resultado.tipo_erro,
    }


def _criar_oferta_classificador() -> Oferta:
    return Oferta(
        nome="Ryzen NVMe",
        loja="Teste",
        preco=999.90,
        preco_antigo=None,
        link="https://example.com/produto",
        imagem=None,
        marketplace="teste",
    )


def _criar_oferta_curadoria() -> Oferta:
    oferta = Oferta(
        nome="Placa de Video RTX 4060 8GB GDDR6",
        loja="Teste",
        preco=2199.0,
        preco_antigo=None,
        link="https://example.com/produto",
        imagem=None,
        marketplace="teste",
    )

    oferta.categoria = "Placa de vídeo"
    oferta.eh_nicho = True
    oferta.relevancia_nicho = 90.0
    oferta.confianca_normalizacao = 70.0

    return oferta


def _avaliar_caso_classificador_mock() -> dict[str, Any]:
    controle = _criar_controle_mock()
    provedor = _criar_provider_mock()

    classificador = ClassificadorProdutoAssistidoAI(
        habilitado=True,
        provedor=provedor,
        controle_operacional=controle,
    )

    resultado = classificador.classificar(_criar_oferta_classificador())

    return {
        "caso": "classificador",
        "gate_ai_acionado": resultado.gate_ai_acionado,
        "diagnostico": {
            "ambiguo": resultado.diagnostico.ambiguo,
            "motivo": resultado.diagnostico.motivo,
            "categorias_topo": list(resultado.diagnostico.categorias_topo),
        },
        "categoria_deterministica": (resultado.classificacao_deterministica.categoria),
        "categoria_final": (resultado.classificacao_final.categoria),
        "inteligencia_ai": _resultado_ai_para_dict(resultado.inteligencia_ai),
        "controle_operacional": asdict(controle.snapshot()),
    }


def _avaliar_caso_curadoria_mock() -> dict[str, Any]:
    controle = _criar_controle_mock()
    provedor = _criar_provider_mock()

    curadoria = CuradoriaPublicacaoAssistidaAI(
        habilitado=True,
        provedor=provedor,
        controle_operacional=controle,
    )

    resultado = curadoria.analisar(_criar_oferta_curadoria())

    return {
        "caso": "curadoria",
        "gate_ai_acionado": resultado.gate_ai_acionado,
        "diagnostico": {
            "motivo": resultado.diagnostico.motivo,
            "sinais": list(resultado.diagnostico.sinais),
        },
        "publicavel_deterministico": (resultado.curadoria_deterministica.publicavel),
        "publicavel_final": (resultado.curadoria_final.publicavel),
        "revisao_manual_sugerida": (resultado.revisao_manual_sugerida),
        "inteligencia_ai": _resultado_ai_para_dict(resultado.inteligencia_ai),
        "controle_operacional": asdict(controle.snapshot()),
    }


def executar_avaliacao_dominios_mock(
    *,
    caso: str = "dominios",
    caminho_relatorio: Path | None = None,
) -> dict[str, Any]:
    if caso not in {
        "classificador",
        "curadoria",
        "dominios",
    }:
        raise ValueError("caso de dominio precisa ser " "classificador, curadoria ou dominios")

    casos: list[dict[str, Any]] = []

    if caso in {
        "classificador",
        "dominios",
    }:
        casos.append(_avaliar_caso_classificador_mock())

    if caso in {
        "curadoria",
        "dominios",
    }:
        casos.append(_avaliar_caso_curadoria_mock())

    relatorio: dict[str, Any] = {
        "schema_version": 1,
        "capturado_em": (datetime.now().astimezone().isoformat(timespec="seconds")),
        "modo": "mock",
        "caso": caso,
        "casos": casos,
        "rede_real_utilizada": False,
    }

    destino = caminho_relatorio if caminho_relatorio is not None else _caminho_relatorio_padrao()

    destino.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destino.write_text(
        json.dumps(
            relatorio,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    relatorio["caminho_relatorio"] = str(destino)

    return relatorio


def main() -> int:
    args = criar_parser().parse_args()

    try:
        if args.caso == "contrato":
            relatorio = executar_avaliacao(
                modo=args.modo,
                permitir_rede_real=(args.permitir_rede_real),
                provider_real=(args.provider_real),
                caminho_relatorio=(args.relatorio),
            )
        else:
            if args.modo != "mock":
                raise RuntimeError("Casos de dominio V20C sao " "permitidos apenas em modo mock.")

            if args.permitir_rede_real:
                raise RuntimeError(
                    "--permitir-rede-real nao pode ser usado " "com casos de dominio V20C."
                )

            if args.provider_real != "generico":
                raise RuntimeError("--provider-real so pode ser usado " "com --caso contrato.")

            relatorio = executar_avaliacao_dominios_mock(
                caso=args.caso,
                caminho_relatorio=(args.relatorio),
            )
    except Exception as erro:
        print("AVALIACAO_PROVIDER_AI_OK=False")
        print("ERRO=" + type(erro).__name__ + ": " + str(erro))
        return 1

    print("AVALIACAO_PROVIDER_AI_OK=True")
    print("MODO=" + str(relatorio["modo"]))

    if args.caso == "contrato":
        resultado = relatorio["resultado"]
        controle = relatorio["controle_operacional"]

        print("PROVIDER_REAL=" + str(relatorio.get("provider_real")))
        print("STATUS=" + str(resultado["status"]))
        print("FALLBACK_USADO=" + str(resultado["fallback_usado"]))
        print("VALIDADA_DETERMINISTICAMENTE=" + str(resultado["validada_deterministicamente"]))
        print(
            "CHAMADAS_EXTERNAS_TOTAL=" + str(controle["observabilidade"]["chamadas_externas_total"])
        )
        print("KILL_SWITCH_ATIVO=" + str(controle["kill_switch_ativo"]))
    else:
        print("CASO=" + str(relatorio["caso"]))
        print("CASOS_TOTAL=" + str(len(relatorio["casos"])))
        print("REDE_REAL_UTILIZADA=" + str(relatorio["rede_real_utilizada"]))

        for item in relatorio["casos"]:
            nome = str(item["caso"]).upper()

            print(nome + "_GATE_AI_ACIONADO=" + str(item["gate_ai_acionado"]))
            print(nome + "_STATUS=" + str(item["inteligencia_ai"]["status"]))
            print(
                nome
                + "_CHAMADAS_EXTERNAS_TOTAL="
                + str(item["controle_operacional"]["observabilidade"]["chamadas_externas_total"])
            )

    print("RELATORIO=" + str(relatorio["caminho_relatorio"]))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
