# ============================================================
# Projeto Renda Automática
# Diagnóstico Completo do Ambiente
# Gera: verificacao_ambiente.txt
# ============================================================

$OutputFile = Join-Path $PSScriptRoot "verificacao_ambiente.txt"

if (Test-Path $OutputFile) {
    Remove-Item $OutputFile -Force
}

function Add-Section($Title) {
    Add-Content $OutputFile ""
    Add-Content $OutputFile "=============================================================="
    Add-Content $OutputFile $Title
    Add-Content $OutputFile "=============================================================="
}

function Run($Command) {
    Add-Content $OutputFile ""
    Add-Content $OutputFile "> $Command"
    Add-Content $OutputFile ""

    try {
        Invoke-Expression $Command 2>&1 | Out-File $OutputFile -Append
    }
    catch {
        $_ | Out-File $OutputFile -Append
    }
}

Add-Section "DATA"

Get-Date | Out-File $OutputFile -Append

Add-Section "SISTEMA"

Run "systeminfo"

Add-Section "PYTHON"

Run "python --version"
Run "python -c `"import sys;print(sys.version)`""
Run "python -c `"import sys;print(sys.executable)`""

Add-Section "PIP"

Run "python -m pip --version"
Run "pip list"
Run "pip check"

Add-Section "PLAYWRIGHT"

Run "python -c `"import playwright;print(playwright.__version__)`""

Run "python -c `"from playwright.sync_api import sync_playwright;p=sync_playwright().start();b=p.chromium.launch(headless=True);print('Chromium OK');b.close();p.stop()`""

Add-Section "DEPENDÊNCIAS"

Run "python -c `"import requests;print(requests.__version__)`""
Run "python -c `"import httpx;print(httpx.__version__)`""
Run "python -c `"import pandas;print(pandas.__version__)`""
Run "python -c `"import numpy;print(numpy.__version__)`""
Run "python -c `"import bs4;print(bs4.__version__)`""
Run "python -c `"import telegram;print(telegram.__version__)`""
Run "python -c `"import dotenv;print(dotenv.__version__)`""

Add-Section "FERRAMENTAS"

Run "black --version"
Run "ruff --version"
Run "isort --version-number"
Run "mypy --version"
Run "pytest --version"
Run "bandit --version"
Run "pip-audit --version"
Run "pre-commit --version"

Add-Section "TESTES"

Run "pytest"

Add-Section "BLACK"

Run "black --check ."

Add-Section "RUFF"

Run "ruff check ."

Add-Section "ISORT"

Run "isort --check-only ."

Add-Section "MYPY"

Run "mypy ."

Add-Section "BANDIT"

Run "bandit -r . -x .venv,tests"

Add-Section "PIP AUDIT"

Run "pip-audit"

Add-Section "PRE-COMMIT"

Run "pre-commit run --all-files"

Add-Section "GIT"

Run "git status"
Run "git branch"
Run "git remote -v"

Write-Host ""
Write-Host "==============================================="
Write-Host "Diagnóstico concluído."
Write-Host ""
Write-Host "Arquivo gerado:"
Write-Host $OutputFile
Write-Host "==============================================="
