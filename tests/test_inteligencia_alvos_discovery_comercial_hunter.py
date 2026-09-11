from datetime import UTC, datetime, timedelta

from models.perfil_comercial_scout import (
    PerfilComercialScout,
)
from models.tendencia_comercial_scout import (
    ObservacaoComercialScout,
    TendenciaComercialScout,
)
from services.scout.agregador_tendencias_comerciais_scout import (
    AgregadorTendenciasComerciaisScout,
)
from services.scout.inteligencia_alvos_discovery_comercial_hunter import (
    InteligenciaAlvosDiscoveryComercialHunter,
)

AGORA = datetime(
    2026,
    9,
    10,
    22,
    30,
    tzinfo=UTC,
)


def _perfil(
    id_externo: str,
    *,
    marketplace: str,
    estrategia: str,
    termos: tuple[str, ...] = (),
    utilizavel: bool = True,
    codigo_voucher: str | None = None,
) -> PerfilComercialScout:
    return PerfilComercialScout(
        fonte="awin",
        id_externo=id_externo,
        tipo_sinal="promotion",
        titulo=f"Campanha {id_externo}",
        marketplace=marketplace,
        codigo_voucher=codigo_voucher,
        estrategia_discovery=estrategia,
        termos_descoberta=termos,
        utilizavel_discovery=utilizavel,
    )


def _observar(
    perfil: PerfilComercialScout,
    horas_atras: int,
) -> ObservacaoComercialScout:
    return ObservacaoComercialScout(
        perfil=perfil,
        observado_em=(
            AGORA
            - timedelta(
                hours=horas_atras,
            )
        ),
    )


def _agregar(
    observacoes,
):
    return AgregadorTendenciasComerciaisScout().agregar(
        list(observacoes),
        agora=AGORA,
        janela_horas=72,
    )


def test_rota_kabum_preserva_marketplace_estrategia_e_termo():
    tendencias = _agregar(
        [
            _observar(
                _perfil(
                    "antigo",
                    marketplace="kabum",
                    estrategia=("buscar_termos_kabum"),
                    termos=("Ryzen 7",),
                ),
                60,
            ),
            _observar(
                _perfil(
                    "novo-1",
                    marketplace="KABUM",
                    estrategia=("buscar_termos_kabum"),
                    termos=("ryzen 7",),
                ),
                20,
            ),
            _observar(
                _perfil(
                    "novo-2",
                    marketplace="kabum",
                    estrategia=("buscar_termos_kabum"),
                    termos=("Ryzen 7",),
                ),
                5,
            ),
        ]
    )

    resultado = InteligenciaAlvosDiscoveryComercialHunter().calcular(
        tendencias,
    )

    assert resultado.houve_alvos is True
    assert len(resultado.alvos) == 1

    alvo = resultado.alvos[0]

    assert alvo.fonte_hunter == "KabumScraper"
    assert alvo.marketplace == "kabum"
    assert alvo.estrategia == ("buscar_termos_kabum")
    assert alvo.termo_busca == "Ryzen 7"
    assert alvo.direcao == "alta"
    assert alvo.sinais_distintos == 3


def test_rota_estavel_madura_tambem_pode_virar_alvo():
    tendencias = _agregar(
        [
            _observar(
                _perfil(
                    "antigo",
                    marketplace="kabum",
                    estrategia=("buscar_termos_kabum"),
                    termos=("SSD NVMe",),
                ),
                60,
            ),
            _observar(
                _perfil(
                    "novo",
                    marketplace="kabum",
                    estrategia=("buscar_termos_kabum"),
                    termos=("SSD NVMe",),
                ),
                5,
            ),
        ]
    )

    resultado = InteligenciaAlvosDiscoveryComercialHunter().calcular(
        tendencias,
    )

    assert len(resultado.alvos) == 1
    assert resultado.alvos[0].direcao == "estavel"
    assert resultado.alvos[0].termo_busca == ("SSD NVMe")


def test_mesmo_termo_sem_rota_utilizavel_nao_vira_alvo():
    tendencias = _agregar(
        [
            _observar(
                _perfil(
                    "antigo",
                    marketplace="kabum",
                    estrategia="ignorar",
                    termos=("RTX 5070",),
                    utilizavel=False,
                ),
                60,
            ),
            _observar(
                _perfil(
                    "novo",
                    marketplace="kabum",
                    estrategia="ignorar",
                    termos=("RTX 5070",),
                    utilizavel=False,
                ),
                5,
            ),
        ]
    )

    resultado = InteligenciaAlvosDiscoveryComercialHunter().calcular(
        tendencias,
    )

    assert resultado.alvos == ()


def test_cupom_recorrente_sozinho_nao_vira_termo_de_busca():
    tendencias = _agregar(
        [
            _observar(
                _perfil(
                    "antigo",
                    marketplace="kabum",
                    estrategia="ignorar",
                    utilizavel=False,
                    codigo_voucher="GAMER10",
                ),
                60,
            ),
            _observar(
                _perfil(
                    "novo",
                    marketplace="kabum",
                    estrategia="ignorar",
                    utilizavel=False,
                    codigo_voucher="gamer10",
                ),
                5,
            ),
        ]
    )

    cupons = [item for item in tendencias if item.dimensao == "cupom"]

    assert len(cupons) == 1

    resultado = InteligenciaAlvosDiscoveryComercialHunter().calcular(
        tendencias,
    )

    assert resultado.alvos == ()


def test_feed_aliexpress_maduro_vira_alvo_sem_termo():
    tendencias = _agregar(
        [
            _observar(
                _perfil(
                    "antigo",
                    marketplace="aliexpress",
                    estrategia=("feed_curado_aliexpress"),
                ),
                60,
            ),
            _observar(
                _perfil(
                    "novo",
                    marketplace="aliexpress",
                    estrategia=("feed_curado_aliexpress"),
                ),
                5,
            ),
        ]
    )

    resultado = InteligenciaAlvosDiscoveryComercialHunter().calcular(
        tendencias,
    )

    assert len(resultado.alvos) == 1

    alvo = resultado.alvos[0]

    assert alvo.fonte_hunter == ("AliExpressScraper")
    assert alvo.termo_busca is None
    assert alvo.estrategia == ("feed_curado_aliexpress")


def test_landing_kabum_sem_url_persistida_ainda_nao_vira_alvo():
    tendencias = _agregar(
        [
            _observar(
                _perfil(
                    "antigo",
                    marketplace="kabum",
                    estrategia=("explorar_landing_kabum"),
                ),
                60,
            ),
            _observar(
                _perfil(
                    "novo",
                    marketplace="kabum",
                    estrategia=("explorar_landing_kabum"),
                ),
                5,
            ),
        ]
    )

    resultado = InteligenciaAlvosDiscoveryComercialHunter().calcular(
        tendencias,
    )

    assert resultado.alvos == ()


def test_rota_em_queda_nao_vira_alvo():
    separador = AgregadorTendenciasComerciaisScout.SEPARADOR_ROTA_DISCOVERY

    tendencia = TendenciaComercialScout(
        dimensao="rota_discovery",
        chave=separador.join(
            (
                "kabum",
                "buscar_termos_kabum",
                "ryzen",
            )
        ),
        rotulo="Ryzen",
        janela_horas=72,
        sinais_distintos=3,
        ocorrencias_anteriores=2,
        ocorrencias_recentes=1,
        direcao="queda",
        evidencias=(
            "qualidade_temporal:aprovada",
            "ambas_metades_tem_sinais",
        ),
    )

    resultado = InteligenciaAlvosDiscoveryComercialHunter().calcular(
        [
            tendencia,
        ]
    )

    assert resultado.alvos == ()


def test_rota_imatura_ou_desconhecida_e_ignorada():
    separador = AgregadorTendenciasComerciaisScout.SEPARADOR_ROTA_DISCOVERY

    imatura = TendenciaComercialScout(
        dimensao="rota_discovery",
        chave=separador.join(
            (
                "kabum",
                "buscar_termos_kabum",
                "ryzen",
            )
        ),
        rotulo="Ryzen",
        janela_horas=72,
        sinais_distintos=3,
        ocorrencias_anteriores=1,
        ocorrencias_recentes=2,
        direcao="alta",
        evidencias=(),
    )

    desconhecida = TendenciaComercialScout(
        dimensao="rota_discovery",
        chave=separador.join(
            (
                "shopee",
                "rota_inexistente",
                "gpu",
            )
        ),
        rotulo="GPU",
        janela_horas=72,
        sinais_distintos=3,
        ocorrencias_anteriores=1,
        ocorrencias_recentes=2,
        direcao="alta",
        evidencias=(
            "qualidade_temporal:aprovada",
            "ambas_metades_tem_sinais",
        ),
    )

    resultado = InteligenciaAlvosDiscoveryComercialHunter().calcular(
        [
            imatura,
            desconhecida,
        ]
    )

    assert resultado.alvos == ()


def test_resultado_nao_contem_social_preco_score_ou_publicacao():
    tendencias = _agregar(
        [
            _observar(
                _perfil(
                    "antigo",
                    marketplace="kabum",
                    estrategia=("buscar_termos_kabum"),
                    termos=("GPU",),
                ),
                60,
            ),
            _observar(
                _perfil(
                    "novo",
                    marketplace="kabum",
                    estrategia=("buscar_termos_kabum"),
                    termos=("GPU",),
                ),
                5,
            ),
        ]
    )

    resultado = InteligenciaAlvosDiscoveryComercialHunter().calcular(
        tendencias,
    )

    alvo = resultado.alvos[0]

    assert resultado.fontes_hunter == ("KabumScraper",)

    assert alvo.fonte_hunter != ("SocialScoutScraper")

    for campo in (
        "preco",
        "score",
        "publicar",
        "aprovada",
    ):
        assert not hasattr(
            alvo,
            campo,
        )
