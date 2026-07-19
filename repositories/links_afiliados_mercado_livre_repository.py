import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from services.identificador_mercado_livre import (
    IdentificadorMercadoLivre
)


@dataclass(frozen=True)
class LinkAfiliadoMercadoLivre:
    item_id: str
    link_original: str
    link_afiliado: str
    criado_em: str
    atualizado_em: str


class LinksAfiliadosMercadoLivreRepository:

    def __init__(
        self,
        caminho_arquivo: str = (
            "database/"
            "links_afiliados_mercado_livre.json"
        )
    ) -> None:

        self.caminho_arquivo = Path(
            caminho_arquivo
        )

        self.identificador = (
            IdentificadorMercadoLivre()
        )

        self._garantir_arquivo()

    def cadastrar(
        self,
        link_original: str,
        link_afiliado: str
    ) -> LinkAfiliadoMercadoLivre:

        resultado = (
            self.identificador.identificar(
                link_original
            )
        )

        item_id = resultado.id_anuncio

        if item_id is None:
            raise ValueError(
                "Não foi possível identificar o "
                "código do anúncio no link original."
            )

        resultado_link = (
            self.identificador.identificar(
                link_afiliado
            )
        )

        if not resultado_link.eh_link_afiliado:
            raise ValueError(
                "O link afiliado precisa ser um "
                "link válido do domínio meli.la."
            )

        dados = self._carregar_dados()

        agora = self._agora_iso()

        registro_anterior = dados.get(
            item_id
        )

        criado_em = agora

        if isinstance(
            registro_anterior,
            dict
        ):
            criado_em = (
                registro_anterior.get(
                    "criado_em",
                    agora
                )
            )

        registro = (
            LinkAfiliadoMercadoLivre(
                item_id=item_id,
                link_original=link_original.strip(),
                link_afiliado=link_afiliado.strip(),
                criado_em=criado_em,
                atualizado_em=agora
            )
        )

        dados[item_id] = asdict(
            registro
        )

        self._salvar_dados(
            dados
        )

        return registro

    def buscar_por_item_id(
        self,
        item_id: str
    ) -> LinkAfiliadoMercadoLivre | None:

        item_id_normalizado = (
            self._normalizar_item_id(
                item_id
            )
        )

        dados = self._carregar_dados()

        registro = dados.get(
            item_id_normalizado
        )

        if not isinstance(
            registro,
            dict
        ):
            return None

        return self._converter_registro(
            item_id=item_id_normalizado,
            registro=registro
        )

    def buscar_por_link(
        self,
        link_original: str
    ) -> LinkAfiliadoMercadoLivre | None:

        resultado = (
            self.identificador.identificar(
                link_original
            )
        )

        if resultado.id_anuncio is None:
            return None

        return self.buscar_por_item_id(
            resultado.id_anuncio
        )

    def obter_link_afiliado(
        self,
        link_original: str
    ) -> str | None:

        registro = self.buscar_por_link(
            link_original
        )

        if registro is None:
            return None

        return registro.link_afiliado

    def existe(
        self,
        link_original: str
    ) -> bool:

        return (
            self.buscar_por_link(
                link_original
            )
            is not None
        )

    def listar(
        self
    ) -> list[
        LinkAfiliadoMercadoLivre
    ]:

        dados = self._carregar_dados()

        registros: list[
            LinkAfiliadoMercadoLivre
        ] = []

        for (
            item_id,
            registro
        ) in dados.items():

            if not isinstance(
                registro,
                dict
            ):
                continue

            registros.append(
                self._converter_registro(
                    item_id=item_id,
                    registro=registro
                )
            )

        return sorted(
            registros,
            key=lambda item:
                item.atualizado_em,
            reverse=True
        )

    def quantidade(
        self
    ) -> int:

        return len(
            self._carregar_dados()
        )

    def remover(
        self,
        item_id: str
    ) -> bool:

        item_id_normalizado = (
            self._normalizar_item_id(
                item_id
            )
        )

        dados = self._carregar_dados()

        if (
            item_id_normalizado
            not in dados
        ):
            return False

        del dados[
            item_id_normalizado
        ]

        self._salvar_dados(
            dados
        )

        return True

    def _converter_registro(
        self,
        item_id: str,
        registro: dict
    ) -> LinkAfiliadoMercadoLivre:

        return LinkAfiliadoMercadoLivre(
            item_id=item_id,
            link_original=str(
                registro.get(
                    "link_original",
                    ""
                )
            ),
            link_afiliado=str(
                registro.get(
                    "link_afiliado",
                    ""
                )
            ),
            criado_em=str(
                registro.get(
                    "criado_em",
                    ""
                )
            ),
            atualizado_em=str(
                registro.get(
                    "atualizado_em",
                    ""
                )
            )
        )

    def _normalizar_item_id(
        self,
        item_id: str
    ) -> str:

        item_id_normalizado = (
            item_id
            .strip()
            .upper()
            .replace("-", "")
            .replace("_", "")
        )

        if not item_id_normalizado.startswith(
            "MLB"
        ):
            raise ValueError(
                "O código do anúncio precisa começar "
                "com MLB."
            )

        parte_numerica = (
            item_id_normalizado[3:]
        )

        if not parte_numerica.isdigit():
            raise ValueError(
                "O código do anúncio possui "
                "formato inválido."
            )

        return item_id_normalizado

    def _garantir_arquivo(
        self
    ) -> None:

        self.caminho_arquivo.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        if self.caminho_arquivo.exists():
            return

        self._salvar_dados({})

    def _carregar_dados(
        self
    ) -> dict[str, dict]:

        self._garantir_arquivo()

        try:

            conteudo = (
                self.caminho_arquivo.read_text(
                    encoding="utf-8"
                )
            )

            dados = json.loads(
                conteudo
            )

        except json.JSONDecodeError as erro:
            raise ValueError(
                "O arquivo de links afiliados do "
                "Mercado Livre contém JSON inválido."
            ) from erro

        if not isinstance(
            dados,
            dict
        ):
            raise ValueError(
                "O catálogo de links afiliados "
                "precisa ser um objeto JSON."
            )

        return dados

    def _salvar_dados(
        self,
        dados: dict[str, dict]
    ) -> None:

        conteudo = json.dumps(
            dados,
            ensure_ascii=False,
            indent=4,
            sort_keys=True
        )

        arquivo_temporario = (
            self.caminho_arquivo.with_suffix(
                ".tmp"
            )
        )

        arquivo_temporario.write_text(
            conteudo,
            encoding="utf-8"
        )

        arquivo_temporario.replace(
            self.caminho_arquivo
        )

    def _agora_iso(
        self
    ) -> str:

        return (
            datetime.now(
                timezone.utc
            )
            .isoformat()
        )