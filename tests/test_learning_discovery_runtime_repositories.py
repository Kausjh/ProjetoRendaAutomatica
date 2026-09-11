from pathlib import Path

from repositories.relatorios_repository import (
    RelatoriosRepository,
)


def test_relatorios_repository_expoe_listar(
    tmp_path,
):
    arquivo = tmp_path / "relatorios.json"

    repo = RelatoriosRepository(str(arquivo))

    repo.salvar(
        {
            "valor": 1,
        }
    )

    repo.salvar(
        {
            "valor": 2,
        }
    )

    relatorios = repo.listar()

    assert [item["valor"] for item in relatorios] == [
        1,
        2,
    ]


def test_listar_e_somente_leitura(
    tmp_path,
):
    arquivo = tmp_path / "relatorios.json"

    repo = RelatoriosRepository(str(arquivo))

    repo.salvar(
        {
            "valor": 1,
        }
    )

    primeira = repo.listar()

    segunda = repo.listar()

    assert primeira == segunda

    assert len(segunda) == 1


def test_reader_learning_delega_para_reader_existente():
    arquivo = Path("repositories/" "fila_publicacao_repository.py")

    texto = arquivo.read_text(encoding="utf-8-sig")

    assert "def historico_publicacoes_discovery_comercial_learning(" in texto

    assert "self.historico_publicacoes_discovery_comercial(" in texto

    assert "limite: int = 5000" in texto
