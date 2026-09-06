import sqlite3
from datetime import UTC, datetime, timedelta
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


def _forcar_tempos(
    repo,
    msg,
    *,
    criado_em: datetime,
    atualizado_em: datetime,
):
    formato = "%Y-%m-%d %H:%M:%S"

    with sqlite3.connect(repo.caminho_arquivo) as conexao:
        conexao.execute(
            """
            UPDATE processamentos_social_scout
            SET criado_em = ?,
                atualizado_em = ?
            WHERE fonte = ?
              AND chat_id = ?
              AND message_id = ?
              AND versao_processador = ?
            """,
            (
                criado_em.astimezone(UTC).strftime(formato),
                atualizado_em.astimezone(UTC).strftime(formato),
                msg.fonte,
                msg.chat_id,
                msg.message_id,
                "1",
            ),
        )


def test_status_permanente_continua_terminal_mesmo_antigo(
    tmp_path,
):
    repo = ProcessamentosSocialScoutRepository(tmp_path / "social.sqlite3")

    msg = mensagem()

    repo.salvar(
        msg,
        "1",
        "abc",
        "ignorada",
        "fora_do_escopo",
    )

    agora = datetime(
        2026,
        9,
        6,
        20,
        0,
        tzinfo=UTC,
    )

    _forcar_tempos(
        repo,
        msg,
        criado_em=(agora - timedelta(days=30)),
        atualizado_em=(agora - timedelta(days=30)),
    )

    assert repo.esta_processada(
        msg,
        "1",
        "abc",
        agora_utc=agora,
    )


def test_preco_rejeitado_respeita_cooldown(
    tmp_path,
):
    repo = ProcessamentosSocialScoutRepository(tmp_path / "social.sqlite3")

    msg = mensagem()

    repo.salvar(
        msg,
        "1",
        "abc",
        "preco_rejeitado",
        "produto_oficial_indisponivel",
    )

    agora = datetime(
        2026,
        9,
        6,
        20,
        0,
        tzinfo=UTC,
    )

    _forcar_tempos(
        repo,
        msg,
        criado_em=(agora - timedelta(hours=1)),
        atualizado_em=(agora - timedelta(minutes=10)),
    )

    assert repo.esta_processada(
        msg,
        "1",
        "abc",
        agora_utc=agora,
    )


def test_preco_rejeitado_entra_em_retry_apos_ttl(
    tmp_path,
):
    repo = ProcessamentosSocialScoutRepository(tmp_path / "social.sqlite3")

    msg = mensagem()

    repo.salvar(
        msg,
        "1",
        "abc",
        "preco_rejeitado",
        "preco_divergente",
    )

    agora = datetime(
        2026,
        9,
        6,
        20,
        0,
        tzinfo=UTC,
    )

    _forcar_tempos(
        repo,
        msg,
        criado_em=(agora - timedelta(hours=1)),
        atualizado_em=(agora - timedelta(minutes=16)),
    )

    assert (
        repo.esta_processada(
            msg,
            "1",
            "abc",
            agora_utc=agora,
        )
        is False
    )


def test_preco_rejeitado_para_apos_janela_maxima(
    tmp_path,
):
    repo = ProcessamentosSocialScoutRepository(tmp_path / "social.sqlite3")

    msg = mensagem()

    repo.salvar(
        msg,
        "1",
        "abc",
        "preco_rejeitado",
        "preco_divergente",
    )

    agora = datetime(
        2026,
        9,
        6,
        20,
        0,
        tzinfo=UTC,
    )

    _forcar_tempos(
        repo,
        msg,
        criado_em=(
            agora
            - timedelta(
                hours=6,
                minutes=1,
            )
        ),
        atualizado_em=(agora - timedelta(minutes=20)),
    )

    assert repo.esta_processada(
        msg,
        "1",
        "abc",
        agora_utc=agora,
    )


def test_nao_resolvida_entra_em_retry_apos_30_minutos(
    tmp_path,
):
    repo = ProcessamentosSocialScoutRepository(tmp_path / "social.sqlite3")

    msg = mensagem()

    repo.salvar(
        msg,
        "1",
        "abc",
        "nao_resolvida",
        "destino_nao_resolvido",
    )

    agora = datetime(
        2026,
        9,
        6,
        20,
        0,
        tzinfo=UTC,
    )

    _forcar_tempos(
        repo,
        msg,
        criado_em=(agora - timedelta(hours=2)),
        atualizado_em=(agora - timedelta(minutes=31)),
    )

    assert (
        repo.esta_processada(
            msg,
            "1",
            "abc",
            agora_utc=agora,
        )
        is False
    )


def test_nao_resolvida_para_apos_12_horas(
    tmp_path,
):
    repo = ProcessamentosSocialScoutRepository(tmp_path / "social.sqlite3")

    msg = mensagem()

    repo.salvar(
        msg,
        "1",
        "abc",
        "nao_resolvida",
        "destino_nao_resolvido",
    )

    agora = datetime(
        2026,
        9,
        6,
        20,
        0,
        tzinfo=UTC,
    )

    _forcar_tempos(
        repo,
        msg,
        criado_em=(
            agora
            - timedelta(
                hours=12,
                minutes=1,
            )
        ),
        atualizado_em=(agora - timedelta(hours=1)),
    )

    assert repo.esta_processada(
        msg,
        "1",
        "abc",
        agora_utc=agora,
    )


def test_fingerprint_novo_reinicia_janela_retry(
    tmp_path,
):
    repo = ProcessamentosSocialScoutRepository(tmp_path / "social.sqlite3")

    msg = mensagem()

    repo.salvar(
        msg,
        "1",
        "abc",
        "preco_rejeitado",
        "preco_divergente",
    )

    antigo = datetime(
        2020,
        1,
        1,
        tzinfo=UTC,
    )

    _forcar_tempos(
        repo,
        msg,
        criado_em=antigo,
        atualizado_em=antigo,
    )

    repo.salvar(
        msg,
        "1",
        "def",
        "preco_rejeitado",
        "preco_divergente",
    )

    estado = repo.obter(
        msg,
        "1",
    )

    assert estado is not None

    assert estado["fingerprint"] == "def"

    assert not estado["criado_em"].startswith("2020-01-01")
