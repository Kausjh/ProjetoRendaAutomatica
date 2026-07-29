import re
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlparse


@dataclass(frozen=True)
class ResultadoIdentificacaoMercadoLivre:
    id_produto: str | None
    id_anuncio: str | None
    dominio: str
    url_original: str
    eh_link_afiliado: bool


class IdentificadorMercadoLivre:

    PADRAO = re.compile(r"MLB[\-_]?\d+", re.IGNORECASE)

    DOMINIOS = {
        "mercadolivre.com.br",
        "www.mercadolivre.com.br",
        "produto.mercadolivre.com.br",
    }

    DOMINIOS_AFILIADOS = {
        "meli.la",
        "www.meli.la",
    }

    def identificar(self, link: str) -> ResultadoIdentificacaoMercadoLivre:

        url = urlparse(link)

        host = (url.hostname or "").lower()

        query = parse_qs(url.query)

        id_anuncio = None
        id_produto = None

        # -------------------------
        # anúncio
        # -------------------------

        if "wid" in query:

            id_anuncio = self._extrair(query["wid"][0])

        elif "item_id" in query:

            id_anuncio = self._extrair(query["item_id"][0])

        elif "pdp_filters" in query:

            texto = unquote(query["pdp_filters"][0])

            id_anuncio = self._extrair(texto)

        # -------------------------
        # produto
        # -------------------------

        caminhos = self.PADRAO.findall(url.path)

        if caminhos:

            id_produto = self._normalizar(caminhos[-1])

        return ResultadoIdentificacaoMercadoLivre(
            id_produto=id_produto,
            id_anuncio=id_anuncio,
            dominio=host,
            url_original=link,
            eh_link_afiliado=host in self.DOMINIOS_AFILIADOS,
        )

    def _extrair(self, texto: str) -> str | None:

        match = self.PADRAO.search(texto)

        if match is None:
            return None

        return self._normalizar(match.group())

    def _normalizar(self, texto: str) -> str:

        return texto.upper().replace("-", "").replace("_", "")
