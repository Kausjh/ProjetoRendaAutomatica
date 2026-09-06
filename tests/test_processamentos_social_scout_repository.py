from pathlib import Path

# 63.8738, -149.7525
from models.mensagem_social_scout import (
    MensagemSocialScout,
)
from repositories.processamentos_social_scout_repository import (
    ProcessamentosSocialScoutRepository,
)


def mensagem(
    texto: str = "Mouse Gamer Teste",
):
    return MensagemSocialScout(
        fonte="telegram",
        chat_id="-100123",
        message_id=10,
        chat_titulo="Grupo Teste",
        texto=texto,
        links=("https://meli.la/teste",),
    )


def test_mensagem_ainda_nao_processada(
    tmp_path,
):
    repo = ProcessamentosSocialScoutRepository(tmp_path / "social.sqlite3")

    assert (
        repo.esta_processada(
            mensagem(),
            "1",
            "abc",
        )
        is False
    )


def test_salva_e_reconhece_mesmo_fingerprint(
    tmp_path,
):
    repo = ProcessamentosSocialScoutRepository(tmp_path / "social.sqlite3")

    msg = mensagem()

    repo.salvar(
        msg,
        "1",
        "abc",
        "emitida",
        "teste",
    )

    assert repo.esta_processada(
        msg,
        "1",
        "abc",
    )

    assert repo.quantidade() == 1


def test_fingerprint_novo_libera_reprocessamento(
    tmp_path,
):
    repo = ProcessamentosSocialScoutRepository(tmp_path / "social.sqlite3")

    msg = mensagem()

    repo.salvar(
        msg,
        "1",
        "abc",
        "emitida",
    )

    assert (
        repo.esta_processada(
            msg,
            "1",
            "def",
        )
        is False
    )


def test_versao_nova_libera_reprocessamento(
    tmp_path,
):
    repo = ProcessamentosSocialScoutRepository(tmp_path / "social.sqlite3")

    msg = mensagem()

    repo.salvar(
        msg,
        "1",
        "abc",
        "emitida",
    )

    assert (
        repo.esta_processada(
            msg,
            "2",
            "abc",
        )
        is False
    )


def test_estado_persiste_entre_instancias(
    tmp_path,
):
    banco = tmp_path / "social.sqlite3"

    msg = mensagem()

    primeiro = ProcessamentosSocialScoutRepository(banco)

    primeiro.salvar(
        msg,
        "1",
        "abc",
        "ignorada",
        "fora_do_escopo",
    )

    segundo = ProcessamentosSocialScoutRepository(banco)

    estado = segundo.obter(
        msg,
        "1",
    )

    assert estado is not None
    assert estado["fingerprint"] == "abc"
    assert estado["status"] == "ignorada"
    assert estado["motivo"] == "fora_do_escopo"


def test_arquivo_sqlite_e_liberado_imediatamente(
    tmp_path,
):
    caminho = tmp_path / "social.sqlite3"

    repo = ProcessamentosSocialScoutRepository(caminho)

    msg = mensagem()

    repo.salvar(
        msg,
        "1",
        "abc",
        "emitida",
        "teste",
    )

    assert (
        repo.obter(
            msg,
            "1",
        )
        is not None
    )

    assert repo.quantidade() == 1

    # No Windows isso falha com WinError 32
    # se alguma conexao SQLite continuar aberta.
    caminho.unlink()

    assert not caminho.exists()

    Path(str(caminho) + "-wal").unlink(missing_ok=True)

    Path(str(caminho) + "-shm").unlink(missing_ok=True)
