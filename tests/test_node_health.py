import json

from services.infra import node_health


def _processo(
    pid,
    parent_pid,
    nome,
    comando,
    memoria_rss_bytes=None,
):
    return node_health.ProcessoNode(
        pid=pid,
        parent_pid=parent_pid,
        nome=nome,
        linha_comando=comando,
        memoria_rss_bytes=memoria_rss_bytes,
    )


def test_snapshot_detecta_componentes_do_node(
    monkeypatch,
    tmp_path,
):
    projeto = tmp_path / "ProjetoRendaAutomatica"

    projeto.mkdir()

    lock = projeto / "execucao_em_andamento.lock"

    lock.write_text(
        json.dumps(
            {
                "pid": 50,
                "iniciado_em": 123.0,
            }
        ),
        encoding="utf-8",
    )

    raiz = str(projeto)

    processos = (
        _processo(
            10,
            1,
            "powershell.exe",
            (f"{raiz}\\scripts\\" "supervisor_renda_automatica.ps1"),
        ),
        _processo(
            20,
            10,
            "python.exe",
            f"{raiz}\\runtime.py",
        ),
        _processo(
            30,
            10,
            "python.exe",
            (f"{raiz}\\" "social_scout_telegram.py"),
        ),
        _processo(
            40,
            20,
            "python.exe",
            f"{raiz}\\bot_consulta.py",
        ),
        _processo(
            45,
            20,
            "python.exe",
            f"{raiz}\\publicador_fila.py",
        ),
        _processo(
            50,
            20,
            "python.exe",
            (f"{raiz}\\services\\launcher\\" "chrome_launcher.py"),
        ),
        _processo(
            60,
            50,
            "chrome.exe",
            (
                "chrome.exe "
                "--remote-debugging-port=9222 "
                f"--user-data-dir={raiz}\\"
                "browser_profile_cdp"
            ),
        ),
    )

    monkeypatch.setattr(
        node_health,
        "_listar_processos",
        lambda: processos,
    )

    monkeypatch.setattr(
        node_health,
        "_cdp_esta_disponivel",
        lambda: True,
    )

    monkeypatch.setattr(
        node_health,
        "_obter_metricas_sistema",
        lambda: node_health.MetricasSistema(
            uptime_segundos=3600.0,
            cpu_percentual=25.0,
            memoria_total_bytes=1000,
            memoria_disponivel_bytes=400,
            memoria_uso_percentual=60.0,
        ),
    )

    monkeypatch.setattr(
        node_health,
        "_metricas_disco",
        lambda diretorio: (
            2000,
            500,
            75.0,
        ),
    )

    estado = node_health.capturar_estado_node(
        node_id="node-a1b2c3d4e5f6",
        diretorio_projeto=projeto,
        caminho_lock=lock,
    )

    servicos = {servico.nome: servico for servico in estado.servicos}

    assert servicos["supervisor"].ativo
    assert servicos["runtime"].ativo
    assert servicos["social_scout"].ativo
    assert servicos["bot_consulta"].ativo
    assert servicos["publicador_fila"].ativo
    assert servicos["chrome_cdp"].ativo
    assert servicos["pipeline"].ativo

    assert servicos["pipeline"].pids == (50,)

    assert estado.quantidade_processos_projeto == 7


def test_snapshot_preserva_metricas_sem_classificar_saude(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        node_health,
        "_listar_processos",
        lambda: (),
    )

    monkeypatch.setattr(
        node_health,
        "_cdp_esta_disponivel",
        lambda: False,
    )

    monkeypatch.setattr(
        node_health,
        "_obter_metricas_sistema",
        lambda: node_health.MetricasSistema(
            uptime_segundos=7200.0,
            cpu_percentual=88.5,
            memoria_total_bytes=1000,
            memoria_disponivel_bytes=100,
            memoria_uso_percentual=90.0,
        ),
    )

    monkeypatch.setattr(
        node_health,
        "_metricas_disco",
        lambda diretorio: (
            1000,
            50,
            95.0,
        ),
    )

    estado = node_health.capturar_estado_node(
        node_id="node-abcdef123456",
        diretorio_projeto=tmp_path,
    )

    dados = estado.para_dict()

    assert dados["cpu_percentual"] == 88.5

    assert dados["memoria_uso_percentual"] == 90.0

    assert dados["disco_uso_percentual"] == 95.0

    assert "status_saude" not in dados
    assert "precisa_reiniciar" not in dados
    assert "reboot" not in dados


def test_snapshot_e_salvo_em_json_atomico(
    tmp_path,
):
    estado = node_health.EstadoNode(
        versao_schema=1,
        node_id="node-a1b2c3d4e5f6",
        coletado_em=("2026-09-09T23:00:00+00:00"),
        sistema="Windows",
        versao_sistema="10",
        arquitetura="AMD64",
        uptime_segundos=100.0,
        cpu_percentual=10.0,
        memoria_total_bytes=1000,
        memoria_disponivel_bytes=800,
        memoria_uso_percentual=20.0,
        disco_total_bytes=2000,
        disco_livre_bytes=1000,
        disco_uso_percentual=50.0,
        quantidade_processos_projeto=0,
        servicos=(),
    )

    caminho = tmp_path / "estado_atual.json"

    resultado = node_health.salvar_estado_node(
        estado,
        caminho,
    )

    assert resultado == caminho

    dados = json.loads(caminho.read_text(encoding="utf-8"))

    assert dados["node_id"] == ("node-a1b2c3d4e5f6")

    assert not (tmp_path / "estado_atual.json.tmp").exists()


def test_snapshot_detecta_node_health_agent_sem_confundir_arquivo_de_teste(
    monkeypatch,
    tmp_path,
):
    projeto = tmp_path / "ProjetoRendaAutomatica"

    projeto.mkdir()

    processos = (
        _processo(
            70,
            1,
            "python.exe",
            f"{projeto}\\node_agent.py",
        ),
        _processo(
            71,
            1,
            "python.exe",
            ("python.exe -m pytest " f"{projeto}\\tests\\" "test_node_agent.py"),
        ),
    )

    monkeypatch.setattr(
        node_health,
        "_listar_processos",
        lambda: processos,
    )

    monkeypatch.setattr(
        node_health,
        "_cdp_esta_disponivel",
        lambda: False,
    )

    monkeypatch.setattr(
        node_health,
        "_obter_metricas_sistema",
        lambda: node_health.MetricasSistema(
            uptime_segundos=100.0,
            cpu_percentual=10.0,
            memoria_total_bytes=1000,
            memoria_disponivel_bytes=500,
            memoria_uso_percentual=50.0,
        ),
    )

    monkeypatch.setattr(
        node_health,
        "_metricas_disco",
        lambda diretorio: (
            2000,
            1000,
            50.0,
        ),
    )

    estado = node_health.capturar_estado_node(
        node_id="node-a1b2c3d4e5f6",
        diretorio_projeto=projeto,
    )

    servicos = {servico.nome: servico for servico in estado.servicos}

    agente = servicos["node_health_agent"]

    assert agente.ativo is True
    assert agente.pids == (70,)


def test_snapshot_mede_memoria_por_componente(
    monkeypatch,
    tmp_path,
):
    projeto = tmp_path / "ProjetoRendaAutomatica"

    projeto.mkdir()

    raiz = str(projeto)

    processos = (
        _processo(
            10,
            1,
            "python.exe",
            f"{raiz}\\runtime.py",
            100,
        ),
        _processo(
            11,
            10,
            "python.exe",
            f"{raiz}\\runtime.py",
            200,
        ),
        _processo(
            20,
            1,
            "python.exe",
            (f"{raiz}\\" "social_scout_telegram.py"),
            50,
        ),
        _processo(
            30,
            1,
            "python.exe",
            f"{raiz}\\node_agent.py",
            25,
        ),
        _processo(
            40,
            1,
            "chrome.exe",
            (
                "chrome.exe "
                "--remote-debugging-port=9222 "
                f"--user-data-dir={raiz}\\"
                "browser_profile_cdp"
            ),
            400,
        ),
        _processo(
            41,
            40,
            "chrome.exe",
            ("chrome.exe --type=utility " f"--user-data-dir={raiz}\\" "browser_profile_cdp"),
            100,
        ),
    )

    monkeypatch.setattr(
        node_health,
        "_listar_processos",
        lambda: processos,
    )

    monkeypatch.setattr(
        node_health,
        "_cdp_esta_disponivel",
        lambda: True,
    )

    monkeypatch.setattr(
        node_health,
        "_obter_metricas_sistema",
        lambda: node_health.MetricasSistema(
            uptime_segundos=100.0,
            cpu_percentual=10.0,
            memoria_total_bytes=5000,
            memoria_disponivel_bytes=1000,
            memoria_uso_percentual=80.0,
        ),
    )

    monkeypatch.setattr(
        node_health,
        "_metricas_disco",
        lambda diretorio: (
            10000,
            5000,
            50.0,
        ),
    )

    estado = node_health.capturar_estado_node(
        node_id="node-a1b2c3d4e5f6",
        diretorio_projeto=projeto,
    )

    servicos = {servico.nome: servico for servico in estado.servicos}

    assert servicos["runtime"].memoria_rss_bytes == 300

    assert servicos["social_scout"].memoria_rss_bytes == 50

    assert servicos["node_health_agent"].memoria_rss_bytes == 25

    assert servicos["chrome_cdp"].memoria_rss_bytes == 500

    assert servicos["chrome_cdp"].pids == (
        40,
        41,
    )

    assert estado.memoria_processos_projeto_bytes == 875


def test_soma_memoria_retorna_none_quando_rss_nao_disponivel():
    processos = (
        _processo(
            1,
            0,
            "python",
            "python app.py",
        ),
    )

    assert node_health._somar_memoria_processos(processos) is None


def test_soma_memoria_conjunto_vazio_retorna_zero():
    assert node_health._somar_memoria_processos(()) == 0
