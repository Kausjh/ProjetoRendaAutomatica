import json
from pathlib import Path

from repositories.historico_precos_repository import (
    HistoricoPrecosRepository,
)


def test_salvar_repete_replace_apos_permission_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    caminho = tmp_path / "historico.json"

    repository = HistoricoPrecosRepository(
        caminho_arquivo=caminho,
    )

    repository.registrar_preco(
        chave_produto="produto-1",
        titulo="Produto Teste",
        link="https://example.com/produto",
        categoria="Teste",
        preco=99.90,
        coletado_em=("2026-08-28T15:00:00-03:00"),
    )

    import repositories.historico_precos_repository as modulo

    replace_real = modulo.os.replace
    chamadas = 0

    def replace_instavel(
        origem,
        destino,
    ):
        nonlocal chamadas

        chamadas += 1

        if chamadas < 3:
            raise PermissionError(
                5,
                "Acesso negado",
            )

        return replace_real(
            origem,
            destino,
        )

    monkeypatch.setattr(
        modulo.os,
        "replace",
        replace_instavel,
    )

    monkeypatch.setattr(
        modulo.time,
        "sleep",
        lambda _: None,
    )

    repository.salvar()

    assert chamadas == 3
    assert caminho.exists()

    dados = json.loads(
        caminho.read_text(
            encoding="utf-8",
        )
    )

    assert dados["produtos"]["produto-1"]["registros"][0]["preco"] == 99.90

    temporarios = list(tmp_path.glob(".historico.*.tmp"))

    assert temporarios == []


def test_salvar_limpa_temporario_se_replace_falhar(
    tmp_path: Path,
    monkeypatch,
) -> None:
    caminho = tmp_path / "historico.json"

    repository = HistoricoPrecosRepository(
        caminho_arquivo=caminho,
    )

    import repositories.historico_precos_repository as modulo

    monkeypatch.setattr(
        modulo.os,
        "replace",
        lambda *_: (_ for _ in ()).throw(
            PermissionError(
                5,
                "Acesso negado",
            )
        ),
    )

    monkeypatch.setattr(
        modulo.time,
        "sleep",
        lambda _: None,
    )

    try:
        repository.salvar()
    except PermissionError:
        pass
    else:
        raise AssertionError("Era esperado PermissionError.")

    assert list(tmp_path.glob(".historico.*.tmp")) == []
