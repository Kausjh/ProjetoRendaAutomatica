class ErroMonetizacaoObrigatoria(RuntimeError):
    """Bloqueia publicacao quando um marketplace exige monetizacao e ela falha."""
