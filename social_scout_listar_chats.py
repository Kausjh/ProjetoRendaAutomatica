# 63.8738, -149.7525

from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from telethon import TelegramClient


def _obrigatoria(
    nome: str,
) -> str:
    valor = os.getenv(
        nome,
        "",
    ).strip()

    if not valor:
        raise ValueError(f"Variavel obrigatoria ausente: {nome}")

    return valor


async def main() -> None:
    load_dotenv()

    api_id = int(_obrigatoria("TELEGRAM_SOCIAL_API_ID"))

    api_hash = _obrigatoria("TELEGRAM_SOCIAL_API_HASH")

    phone = _obrigatoria("TELEGRAM_SOCIAL_PHONE")

    session_path = (
        os.getenv(
            "TELEGRAM_SOCIAL_SESSION",
            "database/social_scout_telegram",
        ).strip()
        or "database/social_scout_telegram"
    )

    cliente = TelegramClient(
        session_path,
        api_id,
        api_hash,
        sequential_updates=True,
    )

    await cliente.start(phone=phone)

    print()
    print("=" * 90)
    print("GRUPOS E CANAIS VISIVEIS PARA O SOCIAL SCOUT")
    print("=" * 90)
    print()

    encontrados = 0

    try:
        async for dialogo in cliente.iter_dialogs():
            if not (dialogo.is_group or dialogo.is_channel):
                continue

            entidade = dialogo.entity

            username = getattr(
                entidade,
                "username",
                None,
            )

            print(f"ID: {dialogo.id}")

            print(f"NOME: {dialogo.name}")

            print("USERNAME: " + (f"@{username}" if username else "-"))

            print("TIPO: " + ("grupo" if dialogo.is_group else "canal"))

            print("-" * 90)

            encontrados += 1

    finally:
        await cliente.disconnect()

    print()
    print(
        "TOTAL DE GRUPOS/CANAIS:",
        encontrados,
    )

    print()
    print("Nenhuma mensagem foi lida " "ou armazenada por este comando.")

    print("Nenhuma mensagem foi enviada.")


if __name__ == "__main__":
    asyncio.run(main())
