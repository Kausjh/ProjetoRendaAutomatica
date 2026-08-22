import random

from services.cadencia_publicacao import CadenciaPublicacao


def test_cadencia_normal_fica_dentro_do_intervalo():
    cadencia = CadenciaPublicacao(
        intervalo_minimo_segundos=60,
        intervalo_maximo_segundos=300,
        intervalo_modo_segundos=120,
        chance_intervalo_curto=0,
        gerador=random.Random(123),
    )

    for _ in range(20):
        intervalo = cadencia.proximo_intervalo("normal")
        assert 60 <= intervalo <= 300


def test_anomalia_forte_recebe_intervalo_urgente():
    cadencia = CadenciaPublicacao(
        urgente_minimo_segundos=8,
        urgente_maximo_segundos=25,
        gerador=random.Random(123),
    )

    intervalo = cadencia.proximo_intervalo("anomalia_forte")

    assert 8 <= intervalo <= 25


def test_intervalo_curto_pode_gerar_duas_publicacoes_no_mesmo_minuto():
    cadencia = CadenciaPublicacao(
        chance_intervalo_curto=1,
        intervalo_curto_minimo_segundos=20,
        intervalo_curto_maximo_segundos=50,
        gerador=random.Random(123),
    )

    intervalo = cadencia.proximo_intervalo("normal")

    assert 20 <= intervalo <= 50
