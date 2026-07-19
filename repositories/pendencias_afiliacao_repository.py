import json
from datetime import datetime
from pathlib import Path

from models.oferta import Oferta


class PendenciasAfiliacaoRepository:

    def __init__(self):

        self.arquivo = (
            Path("database")
            / "pendencias_afiliacao.json"
        )

        self.arquivo.parent.mkdir(
            exist_ok=True
        )

        if not self.arquivo.exists():

            self.salvar([])

    def carregar(self):

        try:

            conteudo = (
                self.arquivo.read_text(
                    encoding="utf-8"
                )
                .strip()
            )

            if not conteudo:
                return []

            return json.loads(
                conteudo
            )

        except (
            FileNotFoundError,
            json.JSONDecodeError,
        ):

            return []

    def salvar(
        self,
        dados,
    ):

        self.arquivo.write_text(
            json.dumps(
                dados,
                indent=4,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def registrar(
        self,
        oferta: Oferta,
    ):

        if oferta.id_anuncio is None:
            return

        pendencias = self.carregar()

        agora = (
            datetime.now()
            .isoformat(timespec="seconds")
        )

        for pendencia in pendencias:

            if (
                pendencia["marketplace"]
                == oferta.marketplace
                and
                pendencia["id_anuncio"]
                == oferta.id_anuncio
            ):

                pendencia["ultima_vez"] = agora
                pendencia["quantidade"] += 1

                self.salvar(
                    pendencias
                )

                return

        pendencias.append(
            {
                "marketplace": oferta.marketplace,
                "id_produto": oferta.id_produto,
                "id_anuncio": oferta.id_anuncio,
                "nome": oferta.nome,
                "link": oferta.link,
                "primeira_vez": agora,
                "ultima_vez": agora,
                "quantidade": 1,
            }
        )

        self.salvar(
            pendencias
        )