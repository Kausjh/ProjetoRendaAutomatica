from __future__ import annotations

from pathlib import Path

from repositories.controle_administrativo_repository import (
    ControleAdministrativoRepository,
)
from services.controle.controlador import (
    ControladorAdministrativo,
)


def _shadow_segmentado(
    *,
    escopo,
    alvo,
    acao_sugerida,
):
    rid = f"shadow:teste:{escopo}:" f"{alvo}:{acao_sugerida}"

    return rid, {
        "disponivel": True,
        "schema_version": 1,
        "shadow": {
            "schema_version": 1,
            "modo": "shadow",
            "disponivel": True,
            "autoridade_operacional": False,
            "executa_automaticamente": False,
            "recomendacoes": [
                {
                    "id": rid,
                    "acao_sugerida": acao_sugerida,
                    "escopo": escopo,
                    "alvo": alvo,
                    "severidade": "critica",
                    "executavel": False,
                    "executada": False,
                    "requer_confirmacao_humana": True,
                    "autoridade_operacional": False,
                }
            ],
        },
    }


def _controlador(
    tmp_path,
    shadow,
):
    repo = ControleAdministrativoRepository(tmp_path / "admin.db")

    controlador = object.__new__(ControladorAdministrativo)
    controlador.repositorio_admin = repo
    controlador.obter_recomendacao_shadow_monetizacao = lambda: shadow

    return (
        controlador,
        repo,
    )


def test_suspender_origem_persiste_e_consumo_replay(
    tmp_path,
):
    rid, shadow = _shadow_segmentado(
        escopo="origem",
        alvo="amazon",
        acao_sugerida=("considerar_isolamento_origem"),
    )

    controlador, repo = _controlador(
        tmp_path,
        shadow,
    )

    primeira = controlador.executar_enforcement_segmentado_monetizacao(
        escopo="origem",
        alvo="amazon",
        acao="suspender",
        confirmacao=("CONFIRMAR_SUSPENDER:" "origem:amazon"),
        recomendacao_id=rid,
        dispositivo="teste",
    )

    segunda = controlador.executar_enforcement_segmentado_monetizacao(
        escopo="origem",
        alvo="amazon",
        acao="suspender",
        confirmacao=("CONFIRMAR_SUSPENDER:" "origem:amazon"),
        recomendacao_id=rid,
        dispositivo="teste",
    )

    assert primeira["executado"] is True
    assert segunda["executado"] is False
    assert (
        repo.enforcement_segmento_monetizacao_ativo(
            "origem",
            "amazon",
        )
        is True
    )


def test_retomar_origem_independe_shadow(
    tmp_path,
):
    controlador, repo = _controlador(
        tmp_path,
        {
            "disponivel": False,
        },
    )

    repo.definir_enforcement_segmento_monetizacao(
        escopo="origem",
        alvo="amazon",
        ativo=True,
        recomendacao_id="r",
    )

    resposta = controlador.executar_enforcement_segmentado_monetizacao(
        escopo="origem",
        alvo="amazon",
        acao="retomar",
        confirmacao=("CONFIRMAR_RETOMAR:" "origem:amazon"),
        dispositivo="teste",
    )

    assert resposta["executado"] is True
    assert (
        repo.enforcement_segmento_monetizacao_ativo(
            "origem",
            "amazon",
        )
        is False
    )


def test_listagem_segmentos_e_read_only(
    tmp_path,
):
    controlador, repo = _controlador(
        tmp_path,
        {
            "disponivel": False,
        },
    )

    repo.definir_enforcement_segmento_monetizacao(
        escopo="afiliador",
        alvo="awin",
        ativo=True,
        recomendacao_id="r2",
    )

    dados = controlador.obter_enforcement_segmentos_monetizacao()

    assert dados["disponivel"] is True
    assert dados["segmentos"][0]["alvo"] == "awin"


def test_servidor_expoe_get_e_post_segmentado():
    fonte = Path("services/controle/servidor_status.py").read_text(encoding="utf-8-sig")

    assert '"/monetizacao/enforcement/segmentos"' in fonte
    assert 'partes[2] == "segmento"' in fonte
    assert '"X-Monetizacao-Alvo"' in fonte
    assert "executar_enforcement_segmentado_monetizacao" in fonte


def test_fail_closed_v21a11_tambem_cobre_segmentado():
    fonte = Path("services/controle/servidor_status.py").read_text(encoding="utf-8-sig")

    inicio = fonte.index("            def do_POST(self) -> None:")
    trecho = fonte[inicio : inicio + 1800]

    assert '"/monetizacao/enforcement/"' in trecho
    assert "and not token_administrativo" in trecho
    assert "503" in trecho


# 63.8738, -149.7525


def test_suspender_case_insensitive_preserva_anti_replay(
    tmp_path,
):
    rid, shadow = _shadow_segmentado(
        escopo="origem",
        alvo="amazon",
        acao_sugerida=("considerar_isolamento_origem"),
    )

    controlador, repo = _controlador(
        tmp_path,
        shadow,
    )

    primeira = controlador.executar_enforcement_segmentado_monetizacao(
        escopo="origem",
        alvo="amazon",
        acao="SUSPENDER",
        confirmacao=("CONFIRMAR_SUSPENDER:" "origem:amazon"),
        recomendacao_id=rid,
        dispositivo="teste",
    )

    segunda = controlador.executar_enforcement_segmentado_monetizacao(
        escopo="origem",
        alvo="amazon",
        acao="suspender",
        confirmacao=("CONFIRMAR_SUSPENDER:" "origem:amazon"),
        recomendacao_id=rid,
        dispositivo="teste",
    )

    assert primeira["executado"] is True
    assert segunda["executado"] is False
    assert segunda["decisao"]["motivo"] == "recomendacao_ja_consumida"
    assert (
        repo.enforcement_segmento_monetizacao_ativo(
            "origem",
            "amazon",
        )
        is True
    )
