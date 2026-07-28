"""Infraestrutura compartilhada para automação de navegadores."""

from automation_web.configuracao_navegador import ConfiguracaoNavegador
from automation_web.navegador_persistente import NavegadorPersistente

__all__ = [
    "ConfiguracaoNavegador",
    "NavegadorPersistente",
]
