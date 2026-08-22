from pathlib import Path


def test_logs_de_observabilidade_estao_presentes():
    raiz = Path(__file__).resolve().parents[1]

    repo = (raiz / "repositories" / "fila_publicacao_repository.py").read_text(encoding="utf-8")

    seletor = (raiz / "services" / "seletor_editorial.py").read_text(encoding="utf-8")

    publicador = (raiz / "publicador_fila.py").read_text(encoding="utf-8")

    assert "Família semântica detectada:" in repo
    assert "Anti-duplicata de família:" in repo
    assert "resumo_familias_pendentes" in repo

    assert "Anti-repost: bloqueando família" in seletor
    assert "liberada antes do cooldown" in seletor

    assert "Anti-repost por família ativo:" in publicador
    assert "Snapshot editorial da fila:" in publicador
    assert "confiança família" in publicador
