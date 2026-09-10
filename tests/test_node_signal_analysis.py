import json

from services.infra.node_signal_analysis import (
    analisar_sinais_node,
    salvar_sinais_node,
)


def _json(
    caminho,
    valor,
):
    caminho.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    caminho.write_text(
        json.dumps(valor),
        encoding="utf-8",
    )


def _historico(
    diretorio,
    registros,
):
    diretorio.mkdir(
        parents=True,
        exist_ok=True,
    )

    (diretorio / "2026-09-10.jsonl").write_text(
        "\n".join(json.dumps(registro) for registro in registros) + "\n",
        encoding="utf-8",
    )


def _servico(
    nome,
    ativo=True,
    pids=None,
):
    return {
        "nome": nome,
        "ativo": ativo,
        "pids": ([1] if pids is None and ativo else ([] if pids is None else pids)),
    }


def _estado(
    *,
    servicos=None,
    processos=10,
):
    if servicos is None:
        servicos = [
            _servico("supervisor"),
            _servico("node_health_agent"),
            _servico("social_scout"),
            _servico("runtime"),
            _servico("bot_consulta"),
            _servico("publicador_fila"),
            _servico("chrome_cdp"),
            _servico(
                "pipeline",
                ativo=False,
                pids=[],
            ),
        ]

    return {
        "node_id": "node-a1b2c3d4e5f6",
        "coletado_em": ("2026-09-10T10:00:00+00:00"),
        "quantidade_processos_projeto": processos,
        "servicos": servicos,
    }


def _qualidade(
    *,
    ram_comparavel=False,
):
    return {
        "janela_recente": {
            "amostras_esperadas": 13,
            "amostras_observadas": 13,
            "razao_amostras_percentual": 100.0,
            "gaps_igual_ou_acima_2x_cadencia": 0,
            "timestamps_repetidos": 0,
        },
        "metricas": [
            {
                "nome": "cpu_percentual",
                "comparacao_disponivel": True,
                "percentual_presenca_recente": 100.0,
                "percentual_presenca_baseline": 100.0,
            },
            {
                "nome": "memoria_host_percentual",
                "comparacao_disponivel": True,
                "percentual_presenca_recente": 100.0,
                "percentual_presenca_baseline": 100.0,
            },
            {
                "nome": ("memoria_processos_projeto_bytes"),
                "comparacao_disponivel": ram_comparavel,
                "percentual_presenca_recente": (100.0 if ram_comparavel else 50.0),
                "percentual_presenca_baseline": (100.0 if ram_comparavel else 0.0),
            },
            {
                "nome": "quantidade_processos_projeto",
                "comparacao_disponivel": True,
                "percentual_presenca_recente": 100.0,
                "percentual_presenca_baseline": 100.0,
            },
        ],
    }


def _comparativo(
    *,
    atual=10,
    recente=10,
    baseline=10,
    inclinacao=0,
    n_recente=13,
    n_baseline=71,
):
    return {
        "atual": atual,
        "media_recente": recente,
        "media_baseline": baseline,
        "delta_media_absoluto": (recente - baseline if baseline is not None else None),
        "delta_media_percentual": None,
        "inclinacao_recente_por_hora": inclinacao,
        "amostras_recente": n_recente,
        "amostras_baseline": n_baseline,
    }


def _tendencia(
    *,
    ram=None,
    host=None,
):
    if ram is None:
        ram = _comparativo(
            atual=100,
            recente=100,
            baseline=None,
            inclinacao=10,
            n_recente=7,
            n_baseline=0,
        )

    if host is None:
        host = _comparativo()

    return {
        "cpu_percentual": _comparativo(),
        "memoria_host_percentual": host,
        "memoria_processos_projeto_bytes": ram,
        "quantidade_processos_projeto": (_comparativo()),
    }


def _analisar(
    tmp_path,
    *,
    estado=None,
    qualidade=None,
    tendencia=None,
    historico=None,
):
    caminho_estado = tmp_path / "estado.json"

    caminho_qualidade = tmp_path / "qualidade.json"

    caminho_tendencia = tmp_path / "tendencia.json"

    diretorio_historico = tmp_path / "historico"

    if estado is None:
        estado = _estado()

    if qualidade is None:
        qualidade = _qualidade()

    if tendencia is None:
        tendencia = _tendencia()

    if historico is None:
        historico = [estado]

    _json(
        caminho_estado,
        estado,
    )

    _json(
        caminho_qualidade,
        qualidade,
    )

    _json(
        caminho_tendencia,
        tendencia,
    )

    _historico(
        diretorio_historico,
        historico,
    )

    return analisar_sinais_node(
        caminho_estado,
        caminho_tendencia,
        caminho_qualidade,
        diretorio_historico,
    )


def test_pipeline_inativo_nao_gera_sinal(
    tmp_path,
):
    analise = _analisar(tmp_path)

    codigos = {sinal.codigo for sinal in analise.sinais}

    assert not any(codigo.endswith(":pipeline") for codigo in codigos)


def test_servico_continuo_ausente_gera_sinal(
    tmp_path,
):
    estado = _estado()

    for servico in estado["servicos"]:
        if servico["nome"] == "runtime":
            servico["ativo"] = False
            servico["pids"] = []

    analise = _analisar(
        tmp_path,
        estado=estado,
    )

    assert any(sinal.codigo == "servico_continuo_ausente_atual:runtime" for sinal in analise.sinais)


def test_amostra_sem_autovisibilidade_suprime_quedas(
    tmp_path,
):
    servicos = [
        _servico(
            nome,
            ativo=False,
            pids=[],
        )
        for nome in (
            "supervisor",
            "node_health_agent",
            "social_scout",
            "runtime",
            "bot_consulta",
            "publicador_fila",
            "chrome_cdp",
        )
    ]

    servicos.append(
        _servico(
            "pipeline",
            ativo=False,
            pids=[123],
        )
    )

    estado = _estado(
        servicos=servicos,
        processos=0,
    )

    analise = _analisar(
        tmp_path,
        estado=estado,
    )

    assert not any(
        sinal.codigo.startswith("servico_continuo_ausente_atual:") for sinal in analise.sinais
    )

    assert not any(
        sinal.codigo.startswith("dependencia_persistente_ausente_atual:")
        for sinal in analise.sinais
    )

    assert any(supressao.codigo == "presenca_servicos_atual" for supressao in analise.supressoes)


def test_historico_registra_amostra_sem_autovisibilidade(
    tmp_path,
):
    normal = _estado()

    ruim = _estado(
        servicos=[
            _servico(
                nome,
                ativo=False,
                pids=[],
            )
            for nome in (
                "supervisor",
                "node_health_agent",
                "social_scout",
                "runtime",
                "bot_consulta",
                "publicador_fila",
                "chrome_cdp",
                "pipeline",
            )
        ],
        processos=0,
    )

    ruim["coletado_em"] = "2026-09-10T09:55:00+00:00"

    analise = _analisar(
        tmp_path,
        historico=[
            ruim,
            normal,
        ],
    )

    sinal = next(
        sinal
        for sinal in analise.sinais
        if sinal.codigo == ("amostra_sem_autovisibilidade_" "processos_recente")
    )

    assert sinal.evidencias["quantidade_amostras"] == 1


def test_ram_sem_baseline_e_suprimida(
    tmp_path,
):
    analise = _analisar(tmp_path)

    assert any(
        supressao.codigo == ("tendencia_recurso:" "memoria_processos_projeto_bytes")
        for supressao in analise.supressoes
    )

    assert not any(
        sinal.codigo == ("recurso_acima_baseline_e_subindo:" "memoria_processos_projeto_bytes")
        for sinal in analise.sinais
    )


def test_recurso_com_evidencia_e_direcao_consistente_gera_sinal(
    tmp_path,
):
    host = _comparativo(
        atual=80,
        recente=70,
        baseline=60,
        inclinacao=5,
    )

    analise = _analisar(
        tmp_path,
        tendencia=_tendencia(host=host),
    )

    sinal = next(
        sinal
        for sinal in analise.sinais
        if sinal.codigo == ("recurso_acima_baseline_e_subindo:" "memoria_host_percentual")
    )

    assert sinal.evidencias["atual"] == 80

    assert sinal.evidencias["media_recente"] == 70

    assert sinal.evidencias["media_baseline"] == 60


def test_cobertura_recente_incompleta_gera_sinal(
    tmp_path,
):
    qualidade = _qualidade()

    qualidade["janela_recente"]["amostras_observadas"] = 12

    analise = _analisar(
        tmp_path,
        qualidade=qualidade,
    )

    assert any(sinal.codigo == "cobertura_coleta_recente_incompleta" for sinal in analise.sinais)


def test_saida_nao_contem_politica_de_saude_ou_reboot(
    tmp_path,
):
    analise = _analisar(tmp_path)

    texto = json.dumps(analise.para_dict())

    for termo in (
        "status_saude",
        "precisa_reiniciar",
        "reboot_recomendado",
        "acao_recomendada",
        "saudavel",
        "degradado",
    ):
        assert termo not in texto


def test_salvamento_e_atomico(
    tmp_path,
):
    analise = _analisar(tmp_path)

    caminho = tmp_path / "sinais.json"

    resultado = salvar_sinais_node(
        analise,
        caminho,
    )

    assert resultado == caminho
    assert caminho.exists()

    assert not caminho.with_suffix(".json.tmp").exists()
