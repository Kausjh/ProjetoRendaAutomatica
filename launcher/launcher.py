# 63.8738, -149.7525

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def limpar():
    os.system("cls" if os.name == "nt" else "clear")


def executar(comando):
    subprocess.run(comando, shell=True, cwd=ROOT)


def iniciar():
    executar(f'"{sys.executable}" main.py')


def atualizar():
    executar("git pull")
    executar(f'"{sys.executable}" -m pip install -r requirements.txt')


def atualizar_e_iniciar():
    atualizar()
    iniciar()


def enviar():
    mensagem = input("\nMensagem do commit: ").strip()

    if not mensagem:
        print("\nMensagem vazia.")
        input("\nENTER para continuar...")
        return

    executar("git add .")
    executar(f'git commit -m "{mensagem}"')
    executar("git push")

    input("\nENTER para continuar...")


while True:
    limpar()

    print("=" * 52)
    print("        Projeto Renda Automática")
    print("=" * 52)

    print("\n1 - Iniciar projeto")
    print("2 - Atualizar projeto")
    print("3 - Atualizar + iniciar")
    print("4 - Enviar alterações ao GitHub")
    print("0 - Sair")

    opcao = input("\nEscolha: ")

    if opcao == "1":
        iniciar()

    elif opcao == "2":
        atualizar()

    elif opcao == "3":
        atualizar_e_iniciar()

    elif opcao == "4":
        enviar()

    elif opcao == "0":
        break