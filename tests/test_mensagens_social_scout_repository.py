from models.mensagem_social_scout import MensagemSocialScout
from repositories.mensagens_social_scout_repository import (
    MensagensSocialScoutRepository,
)


def criar_mensagem(
    *,
    message_id: int = 10,
    texto: str = "RTX 5070 por R$ 3.299 na KaBuM",
) -> MensagemSocialScout:
    return MensagemSocialScout(
        fonte="telegram",
        chat_id="-1001234567890",
        message_id=message_id,
        chat_titulo="Grupo de Ofertas",
        chat_username="grupo_ofertas",
        texto=texto,
        links=("https://www.kabum.com.br/produto/123",),
        enviado_em="2026-09-06T20:00:00+00:00",
    )


def test_salva_mensagem_nova(tmp_path):
    repository = MensagensSocialScoutRepository(tmp_path / "social.sqlite3")

    resultado = repository.salvar(criar_mensagem())

    assert resultado == "novo"
    assert repository.quantidade() == 1


def test_mensagem_identica_fica_inalterada(tmp_path):
    repository = MensagensSocialScoutRepository(tmp_path / "social.sqlite3")

    mensagem = criar_mensagem()

    assert repository.salvar(mensagem) == "novo"
    assert repository.salvar(mensagem) == "inalterado"
    assert repository.quantidade() == 1


def test_edicao_atualiza_mesma_mensagem(tmp_path):
    repository = MensagensSocialScoutRepository(tmp_path / "social.sqlite3")

    original = criar_mensagem()

    editada = MensagemSocialScout(
        fonte=original.fonte,
        chat_id=original.chat_id,
        message_id=original.message_id,
        chat_titulo=original.chat_titulo,
        chat_username=original.chat_username,
        texto="RTX 5070 por R$ 3.199 na KaBuM",
        links=original.links,
        enviado_em=original.enviado_em,
        editado_em="2026-09-06T20:05:00+00:00",
    )

    assert repository.salvar(original) == "novo"
    assert repository.salvar(editada) == "atualizado"

    mensagens = repository.listar()

    assert len(mensagens) == 1
    assert mensagens[0].texto == editada.texto
    assert mensagens[0].editado_em == editada.editado_em


def test_listar_reconstroi_links_como_tuple(tmp_path):
    repository = MensagensSocialScoutRepository(tmp_path / "social.sqlite3")

    mensagem = criar_mensagem()

    repository.salvar(mensagem)

    recuperada = repository.listar()[0]

    assert recuperada == mensagem
    assert isinstance(recuperada.links, tuple)


def test_chats_podem_ter_mesmo_message_id(tmp_path):
    repository = MensagensSocialScoutRepository(tmp_path / "social.sqlite3")

    primeira = criar_mensagem(
        message_id=50,
    )

    segunda = MensagemSocialScout(
        fonte="telegram",
        chat_id="-1009999999999",
        message_id=50,
        chat_titulo="Outro Grupo",
        texto="SSD 2TB em promocao",
    )

    assert repository.salvar(primeira) == "novo"
    assert repository.salvar(segunda) == "novo"

    assert repository.quantidade() == 2


def test_limite_da_listagem(tmp_path):
    repository = MensagensSocialScoutRepository(tmp_path / "social.sqlite3")

    for message_id in range(1, 4):
        repository.salvar(
            criar_mensagem(
                message_id=message_id,
            )
        )

    assert len(repository.listar(limite=2)) == 2
    assert repository.listar(limite=0) == []
