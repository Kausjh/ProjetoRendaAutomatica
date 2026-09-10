import json

import pytest

from services.infra.node_signal_history_analysis import (
    analisar_historico_sinais_node,
    salvar_analise_historico_sinais_node,
)


def _sinal(
    codigo,
    observado,
    transicao,
):
    return {
        "codigo": codigo,
        "origem": "teste",
        "titulo": codigo,
        "observado_agora": observado,
        "transicao_ultimo_ciclo": transicao,
    }


def _registro(
    referencia,
    sinais,
    *,
    node_id="node-teste",
):
    return {
        "versao_schema": 1,
        "node_id": node_id,
        "referencia_temporal": referencia,
        "sinais": sinais,
    }


def _gravar(
    tmp_path,
    registros,
    *,
    extras=None,
):
    diretorio = tmp_path / "historico"

    diretorio.mkdir(
        parents=True,
        exist_ok=True,
    )

    linhas = [json.dumps(registro) for registro in registros]

    if extras:
        linhas.extend(extras)

    (diretorio / "2026-09-10.jsonl").write_text(
        "\n".join(linhas) + "\n",
        encoding="utf-8",
    )

    return diretorio


def _por_codigo(
    analise,
    codigo,
):
    return next(sinal for sinal in analise.sinais if sinal.codigo == codigo)


def test_sinal_continuo_tem_duracao_acompanhada(
    tmp_path,
):
    diretorio = _gravar(
        tmp_path,
        [
            _registro(
                "2026-09-10T10:00:00+00:00",
                [
                    _sinal(
                        "a",
                        True,
                        "novo",
                    )
                ],
            ),
            _registro(
                "2026-09-10T10:05:00+00:00",
                [
                    _sinal(
                        "a",
                        True,
                        "continua_observado",
                    )
                ],
            ),
            _registro(
                "2026-09-10T10:10:00+00:00",
                [
                    _sinal(
                        "a",
                        True,
                        "continua_observado",
                    )
                ],
            ),
        ],
    )

    analise = analisar_historico_sinais_node(diretorio)

    sinal = _por_codigo(
        analise,
        "a",
    )

    assert sinal.observado_agora is True
    assert sinal.quantidade_episodios == 1
    assert sinal.reaparecimentos == 0

    assert sinal.duracao_episodio_atual_segundos == 600.0

    episodio = sinal.episodios[0]

    assert episodio.inicio_confirmado is True
    assert episodio.observacoes_ativas == 3
    assert episodio.aberto_no_fim_da_janela is True


def test_desaparecimento_e_reaparecimento_criam_episodios(
    tmp_path,
):
    diretorio = _gravar(
        tmp_path,
        [
            _registro(
                "2026-09-10T10:00:00+00:00",
                [
                    _sinal(
                        "a",
                        True,
                        "novo",
                    )
                ],
            ),
            _registro(
                "2026-09-10T10:05:00+00:00",
                [
                    _sinal(
                        "a",
                        False,
                        "deixou_de_ser_observado",
                    )
                ],
            ),
            _registro(
                "2026-09-10T10:10:00+00:00",
                [
                    _sinal(
                        "a",
                        False,
                        "continua_nao_observado",
                    )
                ],
            ),
            _registro(
                "2026-09-10T10:15:00+00:00",
                [
                    _sinal(
                        "a",
                        True,
                        "reapareceu",
                    )
                ],
            ),
        ],
    )

    analise = analisar_historico_sinais_node(diretorio)

    sinal = _por_codigo(
        analise,
        "a",
    )

    assert sinal.quantidade_episodios == 2
    assert sinal.reaparecimentos == 1
    assert sinal.observado_agora is True

    assert sinal.episodios[0].duracao_acompanhada_segundos == 300.0

    assert sinal.ultimo_intervalo_entre_episodios_segundos == 600.0


def test_inicio_sem_transicao_conhecida_e_marcado_truncado(
    tmp_path,
):
    diretorio = _gravar(
        tmp_path,
        [
            _registro(
                "2026-09-10T10:00:00+00:00",
                [
                    _sinal(
                        "a",
                        True,
                        "continua_observado",
                    )
                ],
            ),
            _registro(
                "2026-09-10T10:05:00+00:00",
                [
                    _sinal(
                        "a",
                        True,
                        "continua_observado",
                    )
                ],
            ),
        ],
    )

    analise = analisar_historico_sinais_node(diretorio)

    episodio = _por_codigo(
        analise,
        "a",
    ).episodios[0]

    assert episodio.inicio_confirmado is False


def test_apenas_node_mais_recente_e_analisado(
    tmp_path,
):
    diretorio = _gravar(
        tmp_path,
        [
            _registro(
                "2026-09-10T09:00:00+00:00",
                [
                    _sinal(
                        "antigo",
                        True,
                        "novo",
                    )
                ],
                node_id="node-antigo",
            ),
            _registro(
                "2026-09-10T10:00:00+00:00",
                [
                    _sinal(
                        "novo",
                        True,
                        "novo",
                    )
                ],
                node_id="node-novo",
            ),
        ],
    )

    analise = analisar_historico_sinais_node(diretorio)

    assert analise.node_id == "node-novo"

    codigos = {sinal.codigo for sinal in analise.sinais}

    assert codigos == {"novo"}


def test_duplicata_identica_e_ignorada(
    tmp_path,
):
    registro = _registro(
        "2026-09-10T10:00:00+00:00",
        [
            _sinal(
                "a",
                True,
                "novo",
            )
        ],
    )

    diretorio = _gravar(
        tmp_path,
        [
            registro,
            registro,
        ],
    )

    analise = analisar_historico_sinais_node(diretorio)

    assert analise.quantidade_amostras == 1
    assert analise.amostras_duplicadas_ignoradas == 1


def test_duplicata_inconsistente_e_rejeitada(
    tmp_path,
):
    diretorio = _gravar(
        tmp_path,
        [
            _registro(
                "2026-09-10T10:00:00+00:00",
                [
                    _sinal(
                        "a",
                        True,
                        "novo",
                    )
                ],
            ),
            _registro(
                "2026-09-10T10:00:00+00:00",
                [
                    _sinal(
                        "b",
                        True,
                        "novo",
                    )
                ],
            ),
        ],
    )

    with pytest.raises(
        ValueError,
        match="inconsistentes",
    ):
        analisar_historico_sinais_node(diretorio)


def test_linha_invalida_e_ignorada_e_saida_atomica(
    tmp_path,
):
    diretorio = _gravar(
        tmp_path,
        [
            _registro(
                "2026-09-10T10:00:00+00:00",
                [
                    _sinal(
                        "a",
                        True,
                        "novo",
                    )
                ],
            ),
        ],
        extras=[
            "{json quebrado",
        ],
    )

    analise = analisar_historico_sinais_node(diretorio)

    assert analise.linhas_invalidas_ignoradas == 1

    caminho = tmp_path / "analise.json"

    salvar_analise_historico_sinais_node(
        analise,
        caminho,
    )

    assert caminho.exists()

    assert not caminho.with_suffix(".json.tmp").exists()


def test_saida_nao_contem_politica_operacional(
    tmp_path,
):
    diretorio = _gravar(
        tmp_path,
        [
            _registro(
                "2026-09-10T10:00:00+00:00",
                [
                    _sinal(
                        "a",
                        True,
                        "novo",
                    )
                ],
            ),
        ],
    )

    analise = analisar_historico_sinais_node(diretorio)

    texto = json.dumps(analise.para_dict())

    for termo in (
        "status_saude",
        "precisa_reiniciar",
        "reboot_recomendado",
        "acao_recomendada",
        "saudavel",
        "degradado",
        "critico",
    ):
        assert termo not in texto
