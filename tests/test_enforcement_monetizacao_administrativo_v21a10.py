from __future__ import annotations

import types
from pathlib import Path

from services.controle.controlador import (
    ControladorAdministrativo,
)
from services.politica_enforcement_monetizacao import (
    CONFIRMACAO_PAUSAR,
    CONFIRMACAO_RETOMAR,
)

RECOMENDACAO_ID = (
    "shadow:monetizacao:global:geral:" "taxa_bloqueio_critica:" "considerar_pausa_publicador"
)


class RepoAuditoriaFake:
    def __init__(self):
        self.itens = []
        self.enforcement_ids = set()

    def registrar_auditoria(
        self,
        *,
        acao,
        alvo,
        detalhes,
        dispositivo,
        resultado,
    ):
        self.itens.append(
            {
                "acao": acao,
                "alvo": alvo,
                "detalhes": detalhes,
                "dispositivo": dispositivo,
                "resultado": resultado,
            }
        )
        return len(self.itens)

    def reservar_enforcement_monetizacao(
        self,
        recomendacao_id,
    ):
        if recomendacao_id in self.enforcement_ids:
            return False

        self.enforcement_ids.add(recomendacao_id)
        return True

    def concluir_enforcement_monetizacao(
        self,
        recomendacao_id,
    ):
        return recomendacao_id in self.enforcement_ids

    def liberar_enforcement_monetizacao(
        self,
        recomendacao_id,
    ):
        if recomendacao_id not in self.enforcement_ids:
            return False

        self.enforcement_ids.remove(recomendacao_id)
        return True


def _shadow_critico():
    return {
        "disponivel": True,
        "schema_version": 1,
        "shadow": {
            "schema_version": 1,
            "modo": "shadow",
            "disponivel": True,
            "autoridade_operacional": False,
            "executa_automaticamente": False,
            "acao_sugerida_principal": ("considerar_pausa_publicador"),
            "recomendacoes_total": 1,
            "recomendacoes": [
                {
                    "id": RECOMENDACAO_ID,
                    "modo": "shadow",
                    "acao_sugerida": ("considerar_pausa_publicador"),
                    "escopo": "global",
                    "alvo": "geral",
                    "severidade": "critica",
                    "codigo_alerta": ("taxa_bloqueio_critica"),
                    "alerta_id": ("monetizacao:global:geral:" "taxa_bloqueio_critica"),
                    "executavel": False,
                    "executada": False,
                    "requer_confirmacao_humana": True,
                    "autoridade_operacional": False,
                }
            ],
        },
    }


def _controlador_fake():
    controlador = object.__new__(ControladorAdministrativo)
    controlador.repositorio_admin = RepoAuditoriaFake()

    controlador.obter_recomendacao_shadow_monetizacao = types.MethodType(
        lambda self: _shadow_critico(),
        controlador,
    )

    chamadas = []

    def executar(
        self,
        componente,
        acao,
        dispositivo=None,
    ):
        chamadas.append(
            (
                componente,
                acao,
                dispositivo,
            )
        )
        return {
            "sucesso": True,
            "componente": componente,
            "acao": acao,
            "resultado": f"{acao}_ok",
        }

    controlador.executar_acao_operacional = types.MethodType(
        executar,
        controlador,
    )

    return controlador, chamadas


def test_negacao_nao_chama_executor_operacional():
    controlador, chamadas = _controlador_fake()

    resposta = controlador.executar_enforcement_monetizacao(
        acao="pausar",
        confirmacao="errada",
        recomendacao_id=RECOMENDACAO_ID,
        dispositivo="teste",
    )

    assert resposta["permitido"] is False
    assert resposta["executado"] is False
    assert chamadas == []

    assert controlador.repositorio_admin.itens[-1]["resultado"] == "negado"


def test_pausa_confirmada_chama_executor_uma_vez():
    controlador, chamadas = _controlador_fake()

    resposta = controlador.executar_enforcement_monetizacao(
        acao="pausar",
        confirmacao=CONFIRMACAO_PAUSAR,
        recomendacao_id=RECOMENDACAO_ID,
        dispositivo="teste",
    )

    assert resposta["sucesso"] is True
    assert resposta["executado"] is True
    assert resposta["automatico"] is False
    assert chamadas == [
        (
            "publicador",
            "pausar",
            "teste",
        )
    ]

    auditoria = controlador.repositorio_admin.itens[-1]

    assert auditoria["acao"] == ("monetizacao.enforcement." "publicador.pausar")
    assert auditoria["resultado"] == "sucesso"


def test_retomada_confirmada_e_reversivel():
    controlador, chamadas = _controlador_fake()

    resposta = controlador.executar_enforcement_monetizacao(
        acao="retomar",
        confirmacao=CONFIRMACAO_RETOMAR,
        dispositivo="teste",
    )

    assert resposta["sucesso"] is True
    assert chamadas == [
        (
            "publicador",
            "retomar",
            "teste",
        )
    ]


def test_servidor_expoe_post_enforcement_manual():
    fonte = Path("services/controle/servidor_status.py").read_text(encoding="utf-8-sig")

    assert 'partes[0] == "monetizacao"' in fonte
    assert 'partes[1] == "enforcement"' in fonte
    assert 'partes[2] == "publicador"' in fonte
    assert '"X-Monetizacao-Confirmacao"' in fonte
    assert '"X-Monetizacao-Recomendacao-Id"' in fonte
    assert "executar_enforcement_monetizacao" in fonte


def test_post_admin_continua_protegido_por_bearer():
    fonte = Path("services/controle/servidor_status.py").read_text(encoding="utf-8-sig")

    inicio = fonte.index("            def do_POST(self) -> None:")
    trecho = fonte[inicio : inicio + 2200]

    assert '"Authorization"' in trecho
    assert '"Bearer "' in trecho
    assert "hmac.compare_digest" in trecho
    assert "401" in trecho


def test_enforcement_nao_e_chamado_pelos_gets():
    fonte = Path("services/controle/servidor_status.py").read_text(encoding="utf-8-sig")

    inicio_get = fonte.index("            def do_GET(self) -> None:")
    inicio_post = fonte.index("            def do_POST(self) -> None:")

    trecho_get = fonte[inicio_get:inicio_post]

    assert "executar_enforcement_monetizacao" not in trecho_get


def test_enforcement_nao_suporta_origem_ou_afiliador_real():
    fonte = Path("services/politica_enforcement_monetizacao.py").read_text(encoding="utf-8-sig")

    assert "bloquear_afiliador" not in fonte
    assert "isolar_origem" not in fonte
    assert "suspender_afiliador" not in fonte


# 63.8738, -149.7525
