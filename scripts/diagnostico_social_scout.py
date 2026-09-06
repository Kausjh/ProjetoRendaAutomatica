# 63.8738, -149.7525

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from scrapers.social_scout_scraper import (  # noqa: E402
    SocialScoutScraper,
)
from services.scout.observabilidade_social_scout import (  # noqa: E402
    coletar_metricas,
    formatar_relatorio,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=("Exibe metricas agregadas e read-only " "do Social Scout.")
    )

    parser.add_argument(
        "--database",
        default="database/social_scout.sqlite3",
        help=("Caminho do banco SQLite do Social Scout."),
    )

    parser.add_argument(
        "--versao",
        default=(SocialScoutScraper.VERSAO_PROCESSADOR),
        help="Versao do processador a observar.",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Emite o diagnostico em JSON.",
    )

    args = parser.parse_args()

    metricas = coletar_metricas(
        args.database,
        versao_processador=args.versao,
    )

    if args.json:
        print(
            json.dumps(
                metricas.para_dict(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

        return

    print(formatar_relatorio(metricas))


if __name__ == "__main__":
    main()
