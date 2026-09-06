# 63.8738, -149.7525

from __future__ import annotations

import asyncio
import logging
import os

from dotenv import load_dotenv

from services.scout.telegram_social_listener import (
    TelegramSocialListener,
    normalizar_chat_ids,
)


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

    listener = TelegramSocialListener(
        api_id=int(_obrigatoria("TELEGRAM_SOCIAL_API_ID")),
        api_hash=_obrigatoria("TELEGRAM_SOCIAL_API_HASH"),
        phone=_obrigatoria("TELEGRAM_SOCIAL_PHONE"),
        session_path=os.getenv(
            "TELEGRAM_SOCIAL_SESSION",
            "database/social_scout_telegram",
        ).strip()
        or "database/social_scout_telegram",
        chat_ids=normalizar_chat_ids(_obrigatoria("TELEGRAM_SOCIAL_CHAT_IDS")),
    )

    await listener.executar()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format=("%(asctime)s | " "%(levelname)s | " "%(name)s | " "%(message)s"),
    )

    asyncio.run(main())
