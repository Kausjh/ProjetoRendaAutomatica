from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from services.api_aplicacao.controlador import ControladorApiAplicacao
from services.api_aplicacao.servidor import ServidorApiAplicacao


@dataclass(frozen=True)
class ProdutoFake:
    chave_canonica: str
    nome_canonico: str
    categoria: str
    marca: str
    modelo: str
    confianca: float
    anuncios: tuple[object, ...] = ()


@dataclass(frozen=True)
class SnapshotFake:
    chave_canonica: str
    nome_canonico: str
    preco_minimo_atual: float
    preco_maximo_atual: float
    mediana_atual: float
    marketplace_melhor_preco: str
    menor_preco_historico: float
    atualizado_em: str


class CatalogoFake:
    def __init__(self) -> None:
        self.produto = ProdutoFake(
            chave_canonica="rtx_5070",
            nome_canonico="RTX 5070",
            categoria="Placa de video",
            marca="nvidia",
            modelo="RTX 5070",
            confianca=97.0,
        )

    def listar_produtos(self, *, limite: int, offset: int):
        if offset > 0:
            return []
        return [self.produto][:limite]

    def quantidade_produtos(self) -> int:
        return 1

    def obter_produto(self, chave_canonica: str):
        if chave_canonica == self.produto.chave_canonica:
            return self.produto
        return None


class PriceFake:
    def obter_snapshot(self, chave_canonica: str):
        if chave_canonica != "rtx_5070":
            return None
        return SnapshotFake(
            chave_canonica="rtx_5070",
            nome_canonico="RTX 5070",
            preco_minimo_atual=4500.0,
            preco_maximo_atual=5000.0,
            mediana_atual=4750.0,
            marketplace_melhor_preco="kabum",
            menor_preco_historico=4400.0,
            atualizado_em="2026-09-13T10:00:00-03:00",
        )

    def listar_precos_atuais(self, chave_canonica: str):
        if chave_canonica != "rtx_5070":
            return []
        return [
            {
                "marketplace": "kabum",
                "identificador": "sku-1",
                "preco_atual": 4500.0,
            }
        ]

    def listar_historico_paginado(
        self,
        chave_canonica: str,
        *,
        limite: int,
        offset: int,
    ):
        if chave_canonica != "rtx_5070":
            return []
        return [
            {
                "preco": 4500.0,
                "marketplace": "kabum",
            }
        ][offset : offset + limite]


class AlertFake:
    def obter_estado_produto(self, chave_canonica: str):
        if chave_canonica != "rtx_5070":
            return None
        return {
            "eventos_total": 1,
            "eventos_recentes": [{"tipo": "mudanca_preco"}],
        }

    def obter_metricas(self):
        return {
            "eventos": 1,
            "produtos_monitorados": 1,
            "listings_monitorados": 1,
        }

    def listar_eventos(self, *, limite: int, offset: int):
        return [
            {
                "tipo": "mudanca_preco",
                "chave_canonica": "rtx_5070",
            }
        ][offset : offset + limite]


class ControladorHttpFake:
    def health(self):
        return {"status": "ok", "api_version": "v1"}

    def listar_produtos(self, *, limite, offset):
        return {
            "api_version": "v1",
            "total": 1,
            "limite": int(limite),
            "offset": int(offset),
            "itens": [{"chave_canonica": "rtx_5070"}],
        }

    def obter_produto(self, chave_canonica):
        if chave_canonica == "rtx_5070":
            return {
                "api_version": "v1",
                "produto": {"chave_canonica": "rtx_5070"},
            }
        return None

    def listar_historico_produto(
        self,
        chave_canonica,
        *,
        limite,
        offset,
    ):
        if chave_canonica != "rtx_5070":
            return None
        return {
            "api_version": "v1",
            "chave_canonica": chave_canonica,
            "limite": int(limite),
            "offset": int(offset),
            "itens": [],
        }

    def listar_alertas(self, *, limite, offset):
        return {
            "api_version": "v1",
            "total": 0,
            "limite": int(limite),
            "offset": int(offset),
            "itens": [],
        }


def _controlador():
    return ControladorApiAplicacao(
        catalogo_repository=CatalogoFake(),
        price_intelligence_repository=PriceFake(),
        alert_engine_repository=AlertFake(),
    )


def _get_json(url: str, token: str | None = None):
    headers = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers)
    with urlopen(request, timeout=5) as resposta:
        return resposta.status, json.loads(resposta.read().decode("utf-8"))


def test_controlador_serializa_dataclass_e_compoe_produto():
    controlador = _controlador()

    lista = controlador.listar_produtos()
    detalhe = controlador.obter_produto("rtx_5070")

    assert lista["total"] == 1
    assert lista["itens"][0]["chave_canonica"] == "rtx_5070"
    assert lista["itens"][0]["preco"]["preco_minimo_atual"] == 4500.0

    assert detalhe is not None
    assert detalhe["produto"]["nome_canonico"] == "RTX 5070"
    assert detalhe["price_intelligence"]["menor_preco_historico"] == 4400.0
    assert detalhe["alert_engine"]["eventos_total"] == 1


def test_controlador_historico_e_alertas_sao_paginados():
    controlador = _controlador()

    historico = controlador.listar_historico_produto(
        "rtx_5070",
        limite=10,
        offset=0,
    )
    alertas = controlador.listar_alertas(
        limite=10,
        offset=0,
    )

    assert historico is not None
    assert historico["chave_canonica"] == "rtx_5070"
    assert len(historico["itens"]) == 1

    assert alertas["total"] == 1
    assert alertas["itens"][0]["tipo"] == "mudanca_preco"


def test_controlador_produto_ausente_retorna_none():
    controlador = _controlador()

    assert controlador.obter_produto("nao_existe") is None
    assert controlador.listar_historico_produto("nao_existe") is None


def test_servidor_rejeita_bind_remoto_sem_token():
    with pytest.raises(ValueError, match="API_APLICACAO_TOKEN"):
        ServidorApiAplicacao(
            ControladorHttpFake(),
            host="0.0.0.0",
            porta=0,
            token="",
        )


def test_servidor_http_v1_read_only_sem_token_em_loopback():
    servidor = ServidorApiAplicacao(
        ControladorHttpFake(),
        host="127.0.0.1",
        porta=0,
        token="",
    )
    servidor.iniciar()

    try:
        endereco = servidor.endereco
        assert endereco is not None
        _, porta = endereco
        base = f"http://127.0.0.1:{porta}"

        status, health = _get_json(f"{base}/api/v1/health")
        assert status == 200
        assert health == {"status": "ok", "api_version": "v1"}

        status, produtos = _get_json(f"{base}/api/v1/produtos?limite=5&offset=0")
        assert status == 200
        assert produtos["total"] == 1

        status, detalhe = _get_json(f"{base}/api/v1/produtos/rtx_5070")
        assert status == 200
        assert detalhe["produto"]["chave_canonica"] == "rtx_5070"

        status, historico = _get_json(f"{base}/api/v1/produtos/rtx_5070/historico")
        assert status == 200
        assert historico["chave_canonica"] == "rtx_5070"

        status, alertas = _get_json(f"{base}/api/v1/alertas")
        assert status == 200
        assert alertas["itens"] == []

        request = Request(
            f"{base}/api/v1/produtos",
            data=b"{}",
            method="POST",
        )
        with pytest.raises(HTTPError) as erro:
            urlopen(request, timeout=5)
        assert erro.value.code == 405
    finally:
        servidor.encerrar()


def test_token_protege_rotas_de_dados_mas_nao_health():
    servidor = ServidorApiAplicacao(
        ControladorHttpFake(),
        host="127.0.0.1",
        porta=0,
        token="segredo-teste",
    )
    servidor.iniciar()

    try:
        endereco = servidor.endereco
        assert endereco is not None
        _, porta = endereco
        base = f"http://127.0.0.1:{porta}"

        status, health = _get_json(f"{base}/api/v1/health")
        assert status == 200
        assert health["status"] == "ok"

        with pytest.raises(HTTPError) as erro:
            _get_json(f"{base}/api/v1/produtos")
        assert erro.value.code == 401

        status, produtos = _get_json(
            f"{base}/api/v1/produtos",
            token="segredo-teste",
        )
        assert status == 200
        assert produtos["total"] == 1
    finally:
        servidor.encerrar()


def test_runtime_inicia_e_encerra_api_separada():
    fonte = open(
        "runtime.py",
        encoding="utf-8-sig",
    ).read()

    assert "ControladorApiAplicacao" in fonte
    assert "ServidorApiAplicacao" in fonte
    assert "servidor_api.iniciar()" in fonte
    assert "servidor_api.encerrar()" in fonte
    assert "ServidorStatusAdministrativo" in fonte


def test_env_example_documenta_api_aplicacao():
    fonte = open(
        ".env.example",
        encoding="utf-8-sig",
    ).read()

    assert "API_APLICACAO_HOST=127.0.0.1" in fonte
    assert "API_APLICACAO_PORTA=8766" in fonte
    assert "API_APLICACAO_TOKEN=" in fonte
