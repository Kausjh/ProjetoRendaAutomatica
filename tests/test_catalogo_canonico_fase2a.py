from __future__ import annotations

import json
import urllib.request

from models.oferta import Oferta
from repositories.catalogo_canonico_repository import CatalogoCanonicoRepository
from repositories.fila_publicacao_repository import FilaPublicacaoRepository
from services.catalogo_canonico_service import CatalogoCanonicoService
from services.controle.controlador import ControladorAdministrativo
from services.controle.servidor_status import ServidorStatusAdministrativo

TOKEN = "token-catalogo-fase2a"


class OrquestradorFake:
    def __init__(self) -> None:
        self._encerrando = False
        self.processo_pipeline = None
        self.processo_publicador = None
        self.processo_bot = None

    def internet_disponivel(self) -> bool:
        return True

    def telegram_disponivel(self) -> bool:
        return True

    def mercado_livre_disponivel(self) -> bool:
        return True


def criar_oferta(
    *,
    marketplace: str,
    identificador: str,
    chave: str,
    nome: str,
) -> Oferta:
    oferta = Oferta(
        nome=nome,
        loja=marketplace,
        preco=1000.0,
        preco_antigo=None,
        link=f"https://example.com/{marketplace}/{identificador}",
        imagem=None,
        marketplace=marketplace,
        id_anuncio=identificador,
        id_produto=identificador,
    )
    oferta.categoria = "Hardware"
    oferta.marca = "Teste"
    oferta.produto_canonico = nome
    oferta.chave_produto_canonica = chave
    oferta.modelo_produto = nome
    oferta.confianca_normalizacao = 95.0
    return oferta


def requisitar(url: str) -> tuple[int, dict]:
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {TOKEN}"},
    )

    with urllib.request.urlopen(request, timeout=2) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def criar_stack(tmp_path):
    catalogo = CatalogoCanonicoRepository(tmp_path / "catalogo.sqlite3")
    service = CatalogoCanonicoService(catalogo)
    fila = FilaPublicacaoRepository(str(tmp_path / "fila.sqlite3"))

    controlador = ControladorAdministrativo(
        orquestrador=OrquestradorFake(),
        fila=fila,
        verificador_chrome=lambda: True,
        catalogo_canonico_repository=catalogo,
    )

    servidor = ServidorStatusAdministrativo(
        controlador=controlador,
        host="127.0.0.1",
        porta=0,
        token=TOKEN,
    )

    return catalogo, service, controlador, servidor


def test_listagem_paginada_do_catalogo(tmp_path):
    catalogo, service, controlador, _ = criar_stack(tmp_path)

    for indice in range(3):
        resultado = service.observar(
            criar_oferta(
                marketplace="mercado_livre",
                identificador=f"MLB{indice}",
                chave=f"produto_{indice}",
                nome=f"Produto {indice}",
            )
        )
        assert resultado.registrado is True

    primeira = controlador.listar_catalogo_canonico(
        limite=2,
        offset=0,
    )
    segunda = controlador.listar_catalogo_canonico(
        limite=2,
        offset=2,
    )

    assert primeira["disponivel"] is True
    assert primeira["total"] == 3
    assert primeira["quantidade"] == 2
    assert segunda["quantidade"] == 1
    assert catalogo.quantidade_produtos() == 3


def test_conflito_e_persistido_sem_remapeamento(tmp_path):
    catalogo, service, _, _ = criar_stack(tmp_path)

    original = criar_oferta(
        marketplace="mercado_livre",
        identificador="MLB1",
        chave="rtx_4060",
        nome="RTX 4060",
    )
    conflito = criar_oferta(
        marketplace="mercado_livre",
        identificador="MLB1",
        chave="rtx_4070",
        nome="RTX 4070",
    )

    assert service.observar(original).registrado is True

    resultado = service.observar(conflito)

    assert resultado.registrado is False
    assert resultado.status == "conflito_anuncio"

    persistidos = catalogo.listar_conflitos()

    assert len(persistidos) == 1
    assert persistidos[0]["chave_existente"] == "rtx_4060"
    assert persistidos[0]["chave_observada"] == "rtx_4070"

    produto = catalogo.obter_por_anuncio(
        marketplace="mercado_livre",
        identificador="MLB1",
    )

    assert produto is not None
    assert produto.chave_canonica == "rtx_4060"
    assert catalogo.obter_produto("rtx_4070") is None


def test_conflito_repetido_incrementa_ocorrencias(tmp_path):
    catalogo, service, _, _ = criar_stack(tmp_path)

    original = criar_oferta(
        marketplace="mercado_livre",
        identificador="MLB1",
        chave="produto_a",
        nome="Produto A",
    )
    conflito = criar_oferta(
        marketplace="mercado_livre",
        identificador="MLB1",
        chave="produto_b",
        nome="Produto B",
    )

    service.observar(original)
    service.observar(conflito)
    service.observar(conflito)

    persistidos = catalogo.listar_conflitos()

    assert len(persistidos) == 1
    assert persistidos[0]["ocorrencias"] == 2


def test_metricas_do_catalogo(tmp_path):
    _, service, controlador, _ = criar_stack(tmp_path)

    service.observar(
        criar_oferta(
            marketplace="mercado_livre",
            identificador="MLB1",
            chave="produto_a",
            nome="Produto A",
        )
    )
    service.observar(
        criar_oferta(
            marketplace="shopee",
            identificador="SHP1",
            chave="produto_a",
            nome="Produto A",
        )
    )

    dados = controlador.obter_metricas_catalogo_canonico()

    assert dados["disponivel"] is True
    assert dados["metricas"]["produtos"] == 1
    assert dados["metricas"]["anuncios"] == 2
    assert dados["metricas"]["conflitos"] == 0
    assert dados["metricas"]["marketplaces"] == {
        "mercado_livre": 1,
        "shopee": 1,
    }


def test_endpoints_catalogo_sao_read_only(tmp_path):
    catalogo, service, _, servidor = criar_stack(tmp_path)

    service.observar(
        criar_oferta(
            marketplace="mercado_livre",
            identificador="MLB1",
            chave="produto_a",
            nome="Produto A",
        )
    )

    antes = catalogo.obter_metricas()

    servidor.iniciar()

    try:
        porta = servidor._servidor.server_address[1]

        status_catalogo, dados_catalogo = requisitar(
            f"http://127.0.0.1:{porta}/catalogo?limite=10&offset=0"
        )
        status_conflitos, dados_conflitos = requisitar(
            f"http://127.0.0.1:{porta}/catalogo/conflitos?limite=10&offset=0"
        )
        status_metricas, dados_metricas = requisitar(f"http://127.0.0.1:{porta}/catalogo/metricas")

        assert status_catalogo == 200
        assert status_conflitos == 200
        assert status_metricas == 200
        assert dados_catalogo["total"] == 1
        assert dados_conflitos["total"] == 0
        assert dados_metricas["metricas"]["produtos"] == 1
    finally:
        servidor.encerrar()

    assert catalogo.obter_metricas() == antes


def test_controlador_sem_catalogo_falha_de_forma_informativa(
    tmp_path,
):
    fila = FilaPublicacaoRepository(str(tmp_path / "fila.sqlite3"))

    controlador = ControladorAdministrativo(
        orquestrador=OrquestradorFake(),
        fila=fila,
        verificador_chrome=lambda: True,
    )

    assert controlador.obter_metricas_catalogo_canonico() == {
        "disponivel": False,
        "schema_version": 1,
        "metricas": None,
    }


def test_fase2a_nao_implementa_bootstrap():
    from pathlib import Path

    arquivos = (
        "repositories/catalogo_canonico_repository.py",
        "services/controle/controlador.py",
        "services/controle/servidor_status.py",
    )

    for caminho in arquivos:
        texto = Path(caminho).read_text(encoding="utf-8-sig").casefold()

        assert "backfill" not in texto
        assert "bootstrap_catalogo" not in texto


# 63.8738, -149.7525
