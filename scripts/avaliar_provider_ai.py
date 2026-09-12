from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from config.configuracoes import Configuracoes
from models.inteligencia_ai import SolicitacaoInteligenciaAI
from services.controle_operacional_ai import (
    ControleOperacionalInteligenciaAI,
)
from services.inteligencia_assistiva_ai import (
    interpretar_com_inteligencia_assistiva,
)
from services.provedor_http_inteligencia_ai import (
    ProvedorHttpInteligenciaAI,
    criar_provedor_http_inteligencia_ai,
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

    if payload.get("tarefa") != TAREFA_AVALIACAO:
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
            "conteudo": dict(SUGESTAO_ESPERADA),
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


def _criar_provider_real(
    *,
    permitir_rede_real: bool,
) -> tuple[
    ProvedorHttpInteligenciaAI,
    ControleOperacionalInteligenciaAI,
]:
    if not permitir_rede_real:
        raise RuntimeError("Modo real exige --permitir-rede-real.")

    configuracoes = Configuracoes()

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
        provedor, controle = _criar_provider_real(permitir_rede_real=(permitir_rede_real))

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


def main() -> int:
    args = criar_parser().parse_args()

    try:
        relatorio = executar_avaliacao(
            modo=args.modo,
            permitir_rede_real=(args.permitir_rede_real),
            caminho_relatorio=(args.relatorio),
        )
    except Exception as erro:
        print("AVALIACAO_PROVIDER_AI_OK=False")
        print("ERRO=" + type(erro).__name__ + ": " + str(erro))
        return 1

    resultado = relatorio["resultado"]
    controle = relatorio["controle_operacional"]

    print("AVALIACAO_PROVIDER_AI_OK=True")
    print("MODO=" + str(relatorio["modo"]))
    print("STATUS=" + str(resultado["status"]))
    print("FALLBACK_USADO=" + str(resultado["fallback_usado"]))
    print("VALIDADA_DETERMINISTICAMENTE=" + str(resultado["validada_deterministicamente"]))
    print("CHAMADAS_EXTERNAS_TOTAL=" + str(controle["observabilidade"]["chamadas_externas_total"]))
    print("KILL_SWITCH_ATIVO=" + str(controle["kill_switch_ativo"]))
    print("RELATORIO=" + str(relatorio["caminho_relatorio"]))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
