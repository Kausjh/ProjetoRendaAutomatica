from datetime import date
from unittest.mock import Mock, patch

from models.sinal_scout import SinalScout
from repositories.sinais_scout_repository import (
    SinaisScoutRepository,
)
from services.scout.awin_promotions_sensor import (
    AwinPromotionsSensor,
)
from services.scout.radar_scout import (
    RadarScout,
)


def resposta_awin() -> Mock:
    resposta = Mock()

    resposta.raise_for_status.return_value = None

    resposta.json.return_value = {
        "data": [
            {
                "promotionId": 123,
                "type": "voucher",
                "advertiser": {
                    "id": 17729,
                    "name": "Kabum BR",
                    "joined": True,
                },
                "title": "Oferta teste",
                "description": "Descricao",
                "terms": "Termos",
                "startDate": ("2026-09-04T03:00:00+00:00"),
                "endDate": ("2026-09-06T13:00:00+00:00"),
                "url": ("https://www.kabum.com.br/"),
                "urlTracking": ("https://www.awin1.com/" "cread.php?teste=1"),
                "regions": {
                    "all": False,
                    "list": [
                        {
                            "name": "Brazil",
                            "countryCode": "BR",
                        }
                    ],
                },
                "voucher": {
                    "code": "RADAR10",
                    "exclusive": False,
                    "attributable": False,
                },
            }
        ],
        "pagination": {},
    }

    return resposta


def test_sensor_converte_promocao_awin():
    sensor = AwinPromotionsSensor(
        publisher_id="123456",
        api_token="token-teste",
        advertiser_ids=[
            17729,
            18879,
        ],
        page_size=10,
    )

    with patch(
        "services.scout." "awin_promotions_sensor." "requests.post",
        return_value=resposta_awin(),
    ) as post:
        sinais = sensor.buscar_sinais(
            updated_since=date(
                2026,
                9,
                1,
            )
        )

    assert len(sinais) == 1

    sinal = sinais[0]

    assert sinal.fonte == "awin"
    assert sinal.id_externo == "123"
    assert sinal.tipo == "voucher"
    assert sinal.advertiser_id == "17729"
    assert sinal.regioes == ("BR",)

    payload = post.call_args.kwargs["json"]

    assert payload["filters"]["membership"] == "joined"

    assert payload["filters"]["regionCodes"] == ["BR"]

    assert payload["filters"]["updatedSince"] == "2026-09-01"


def test_repository_deduplica_sinal(
    tmp_path,
):
    repository = SinaisScoutRepository(tmp_path / "scout.sqlite3")

    sinal = SinalScout(
        fonte="awin",
        id_externo="123",
        tipo="promotion",
        titulo="Oferta",
        url="https://exemplo.com",
    )

    assert repository.salvar(sinal) == "novo"

    assert repository.salvar(sinal) == "inalterado"

    assert repository.quantidade() == 1


class SensorFake:
    nome = "fake"

    def __init__(self):
        self.updated_since = None

    def buscar_sinais(
        self,
        updated_since=None,
    ):
        self.updated_since = updated_since

        return [
            SinalScout(
                fonte="fake",
                id_externo="1",
                tipo="promotion",
                titulo="Teste",
                url="https://exemplo.com",
            )
        ]


def test_radar_scout_persiste_estado(
    tmp_path,
):
    repository = SinaisScoutRepository(tmp_path / "scout.sqlite3")

    sensor_1 = SensorFake()

    resultado_1 = RadarScout(
        sensores=[sensor_1],
        repository=repository,
    ).executar()

    assert resultado_1.novos == 1
    assert resultado_1.erros == 0

    sensor_2 = SensorFake()

    resultado_2 = RadarScout(
        sensores=[sensor_2],
        repository=repository,
    ).executar()

    assert resultado_2.novos == 0
    assert resultado_2.inalterados == 1
    assert sensor_2.updated_since is not None
