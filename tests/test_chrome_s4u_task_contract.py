# 63.8738, -149.7525

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCRIPT = ROOT / "scripts" / "instalar_chrome_ml_s4u.ps1"


def _texto() -> str:
    return SCRIPT.read_text(
        encoding="utf-8-sig",
    )


def test_task_chrome_ml_usa_s4u_headless():
    texto = _texto()

    assert "RendaAutomatica_MLChrome" in texto

    assert "-LogonType S4U" in texto
    assert '"--headless=new"' in texto

    assert '"--remote-debugging-address=127.0.0.1"' in texto

    assert '"--remote-debugging-port=9222"' in texto

    assert "browser_profile_ml_user" in texto

    assert "-AtStartup" in texto


def test_task_chrome_ml_nao_contem_segredos():
    texto = _texto()

    assert "MERCADO_LIVRE_AFFILIATE_TAG" not in texto

    assert "TELEGRAM_BOT_TOKEN" not in texto
    assert "cookie_value" not in texto
