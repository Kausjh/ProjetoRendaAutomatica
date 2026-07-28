from automation_web.navegador_persistente import NavegadorPersistente


URL_INICIAL = "https://www.mercadolivre.com.br/afiliados"


def main() -> None:
    print()
    print("=" * 60)
    print("Configuração do navegador dedicado")
    print("=" * 60)
    print()
    print(
        "O Chromium será aberto usando o perfil exclusivo "
        "salvo em browser_profile/."
    )
    print()
    print(
        "Faça login no Mercado Livre e navegue até o painel "
        "de afiliados."
    )
    print()
    print(
        "Quando terminar, volte a este terminal e pressione ENTER."
    )
    print()

    try:
        with NavegadorPersistente() as navegador:
            pagina = navegador.pagina
            pagina.goto(
                URL_INICIAL,
                wait_until="domcontentloaded",
            )

            input(
                "Pressione ENTER depois que o login estiver concluído: "
            )

            print()
            print("Sessão salva no perfil dedicado com sucesso.")

    except Exception as erro:
        mensagem = str(erro)

        if "Executable doesn't exist" in mensagem:
            print()
            print("O Chromium do Playwright ainda não está instalado.")
            print("Execute:")
            print()
            print("    py -m playwright install chromium")
            print()
            return

        raise


if __name__ == "__main__":
    main()
