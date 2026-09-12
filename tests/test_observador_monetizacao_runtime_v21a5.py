import inspect

from bots.telegram_bot import TelegramBot
from publicador_fila import PublicadorFila


def test_telegram_registra_resultado_no_observador():
    fonte = inspect.getsource(TelegramBot.enviar_oferta)

    assert "registrar_processamento_seguro" in fonte
    assert "exige_confirmacao=exige_afiliacao" in fonte


def test_publicador_compartilha_observador_com_bot():
    fonte = inspect.getsource(PublicadorFila.__init__)

    assert "self.observador_monetizacao = " "ObservadorMonetizacao" in fonte
    assert "observador_monetizacao=" "self.observador_monetizacao" in fonte


def test_publicador_registra_retry_persistente():
    fonte = inspect.getsource(PublicadorFila._publicar_item)

    assert "registrar_retry_seguro" in fonte
    assert "self.AFILIACAO_RETRY_MINUTOS" in fonte
