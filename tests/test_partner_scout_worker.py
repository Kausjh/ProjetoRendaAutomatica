from pathlib import Path

import pytest

from models.resolucao_scout import ResolucaoScout
from models.sinal_scout import SinalScout
from services.scout.partner_scout_worker import (
    INTERVALO_PADRAO_SEGUNDOS,
    PartnerScoutWorker,
    criar_partner_scout_worker,
)


class RadarResultadoFake:
    sinais_recebidos = 1
    novos = 1
    atualizados = 0
    inalterados = 0


class ResultadoFake:
    radar = RadarResultadoFake()

    eventos_comerciais = 1
    historicos_registrados = 1

    falhas_resolucao = 0
    falhas_historico = 0


class CicloFake:
    def __init__(
        self,
        *,
        falhar_primeiro=False,
    ):
        self.chamadas = 0
        self.falhar_primeiro = falhar_primeiro

    def executar(
        self,
    ):
        self.chamadas += 1

        if self.falhar_primeiro and self.chamadas == 1:
            raise RuntimeError("falha simulada")

        return ResultadoFake()


class SensorFake:
    nome = "sensor_fake"

    def buscar_sinais(
        self,
        updated_since=None,
    ):
        del updated_since

        return [
            SinalScout(
                fonte="awin",
                id_externo="1",
                tipo="promotion",
                titulo=("10% em itens da linha " "PlayNinja."),
                url=("https://www.kabum.com.br/"),
                advertiser_id="123",
                advertiser_nome="Kabum BR",
                descricao=("10% em itens da linha " "PlayNinja."),
                termos=("10% em itens da linha " "PlayNinja."),
                regioes=("BR",),
            )
        ]


class ResolverFake:
    nome = "resolver_fake"

    def suporta(
        self,
        sinal,
    ):
        return sinal.fonte == "awin"

    def resolver(
        self,
        sinal,
    ):
        return ResolucaoScout(
            fonte=sinal.fonte,
            id_externo=sinal.id_externo,
            status="landing_page",
            marketplace="kabum",
            tipo_destino="campanha",
            motivo="teste",
        )


def test_intervalo_padrao_e_trinta_minutos():
    assert INTERVALO_PADRAO_SEGUNDOS == 1800.0


def test_worker_rejeita_intervalo_zero():
    with pytest.raises(
        ValueError,
        match="maior que zero",
    ):
        PartnerScoutWorker(
            CicloFake(),
            intervalo_segundos=0,
        )


def test_worker_executa_um_ciclo():
    ciclo = CicloFake()

    worker = PartnerScoutWorker(
        ciclo,
        intervalo_segundos=1,
    )

    resultado = worker.executar_ciclo()

    assert resultado is not None
    assert ciclo.chamadas == 1


def test_worker_respeita_maximo_de_ciclos():
    ciclo = CicloFake()

    worker = PartnerScoutWorker(
        ciclo,
        intervalo_segundos=0.001,
    )

    ciclos = worker.executar(maximo_ciclos=3)

    assert ciclos == 3
    assert ciclo.chamadas == 3


def test_worker_rejeita_maximo_de_ciclos_zero():
    worker = PartnerScoutWorker(
        CicloFake(),
        intervalo_segundos=1,
    )

    with pytest.raises(
        ValueError,
        match="maior que zero",
    ):
        worker.executar(maximo_ciclos=0)


def test_worker_continua_apos_falha_de_um_ciclo():
    ciclo = CicloFake(falhar_primeiro=True)

    worker = PartnerScoutWorker(
        ciclo,
        intervalo_segundos=0.001,
    )

    ciclos = worker.executar(maximo_ciclos=2)

    assert ciclos == 2
    assert ciclo.chamadas == 2


def test_worker_pode_ser_parado_antes_do_loop():
    ciclo = CicloFake()

    worker = PartnerScoutWorker(
        ciclo,
        intervalo_segundos=1,
    )

    worker.solicitar_parada()

    ciclos = worker.executar()

    assert ciclos == 0
    assert ciclo.chamadas == 0


def test_factory_funciona_com_bancos_temporarios(
    tmp_path,
):
    banco_scout = tmp_path / "scout.sqlite3"

    banco_historico = tmp_path / "historico.sqlite3"

    worker = criar_partner_scout_worker(
        intervalo_segundos=1,
        caminho_scout=banco_scout,
        caminho_historico=banco_historico,
        sensores=[
            SensorFake(),
        ],
        resolvedores=[
            ResolverFake(),
        ],
    )

    assert isinstance(
        worker,
        PartnerScoutWorker,
    )

    assert banco_scout.exists()
    assert banco_historico.exists()

    resultado = worker.executar_ciclo()

    assert resultado.radar.novos == 1

    assert resultado.historicos_registrados == 1


def test_entrypoint_nao_cria_banco_ao_ser_importado():
    raiz = Path(__file__).resolve().parents[1]

    fonte = (raiz / "partner_scout.py").read_text(encoding="utf-8-sig")

    assert "load_dotenv(" in fonte

    assert "override=True" in fonte

    assert '"--once"' in fonte

    assert "criar_partner_scout_worker(" in fonte

    assert 'if __name__ == "__main__":' in fonte
