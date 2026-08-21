from services.runtime.orquestrador import (
    ConfiguracoesRuntime,
    calcular_proxima_execucao,
)


def test_proxima_execucao_normal():
    resultado = calcular_proxima_execucao(
        execucao_anterior=100.0,
        agora=110.0,
        intervalo_segundos=30.0,
    )

    assert resultado == 130.0


def test_proxima_execucao_pula_horarios_atrasados():
    resultado = calcular_proxima_execucao(
        execucao_anterior=100.0,
        agora=171.0,
        intervalo_segundos=30.0,
    )

    assert resultado == 190.0


def test_configuracoes_runtime_rejeitam_intervalo_invalido():
    configuracoes = ConfiguracoesRuntime(intervalo_minutos=0)

    try:
        configuracoes.validar()
    except ValueError as erro:
        assert "RUNTIME_INTERVALO_MINUTOS" in str(erro)
    else:
        raise AssertionError("Era esperado ValueError.")
