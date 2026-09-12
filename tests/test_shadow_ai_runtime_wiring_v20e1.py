from __future__ import annotations

from pathlib import Path

from models.oferta import Oferta
from services.classificador_produto_assistido_ai import (
    ClassificadorProdutoAssistidoAI,
)
from services.curadoria_publicacao import CuradoriaPublicacao
from services.curadoria_publicacao_assistida_ai import (
    CuradoriaPublicacaoAssistidaAI,
)


class ObservadorFake:
    def __init__(self) -> None:
        self.eventos = []

    def registrar_gate_seguro(
        self,
        *,
        consumidor,
        solicitacao,
    ) -> bool:
        self.eventos.append((consumidor, solicitacao.tarefa))
        return True


def _oferta(nome: str) -> Oferta:
    return Oferta(
        nome=nome,
        preco=100.0,
        link="https://example.com/item",
        loja="Teste",
        preco_antigo=150.0,
        imagem="https://example.com/item.jpg",
    )


def test_classificador_shadow_observa_gate_com_ai_desligada() -> None:
    observador = ObservadorFake()
    classificador = ClassificadorProdutoAssistidoAI(
        habilitado=False,
        observador_shadow=observador,
    )
    resultado = classificador.classificar(_oferta("Ryzen NVMe"))
    assert resultado.gate_ai_acionado is True
    assert observador.eventos == [("classificador", "desambiguar_categoria_produto")]
    assert resultado.inteligencia_ai is not None
    assert resultado.inteligencia_ai.fallback_usado is True


def test_classificador_shadow_nao_registra_sem_gate() -> None:
    observador = ObservadorFake()
    classificador = ClassificadorProdutoAssistidoAI(
        habilitado=False,
        observador_shadow=observador,
    )
    resultado = classificador.classificar(_oferta("AMD Ryzen 7 5700X"))
    assert resultado.gate_ai_acionado is False
    assert observador.eventos == []


def test_curadoria_shadow_observa_gate_com_ai_desligada() -> None:
    observador = ObservadorFake()
    curadoria = CuradoriaPublicacaoAssistidaAI(
        curadoria=CuradoriaPublicacao(
            nota_minima=0,
            ativa=True,
        ),
        habilitado=False,
        observador_shadow=observador,
    )

    oferta = _oferta("RTX 4060")
    oferta.categoria = "Placa de video"
    oferta.eh_nicho = True
    oferta.relevancia_nicho = 90
    oferta.confianca_normalizacao = 70

    resultado = curadoria.analisar(oferta)
    assert resultado.gate_ai_acionado is True
    assert observador.eventos == [("curadoria", "interpretar_incerteza_editorial")]
    assert resultado.inteligencia_ai is not None
    assert resultado.inteligencia_ai.fallback_usado is True


def test_main_wira_shadow_sem_ligar_ai_real() -> None:
    texto = Path("main.py").read_text(encoding="utf-8-sig")
    assert "ObservadorShadowAI" in texto
    assert "observador_shadow=observador_shadow_ai" in texto
    assert texto.count("habilitado=False") >= 2
    for proibido in (
        "ProvedorOpenAIResponsesAI",
        "OPENAI_API_KEY",
        "api.openai.com",
    ):
        assert proibido not in texto


def test_shadow_nao_muda_autoridade_deterministica() -> None:
    texto_classificador = Path("services/classificador_produto_assistido_ai.py").read_text(
        encoding="utf-8-sig"
    )
    texto_curadoria = Path("services/curadoria_publicacao_assistida_ai.py").read_text(
        encoding="utf-8-sig"
    )
    assert "registrar_gate_seguro" in texto_classificador
    assert "registrar_gate_seguro" in texto_curadoria
    assert "autoriza_publicacao=True" not in texto_classificador
    assert "autoriza_publicacao=True" not in texto_curadoria
