from __future__ import annotations

import time
import unicodedata
from typing import Iterable

from playwright.sync_api import Locator, Page


CATEGORIAS_ALVO = (
    "Informática",
    "Games",
    "Eletrônicos, Áudio e Vídeo",
    "Celulares e Telefones",
)

SELETOR_CARD = "li.poly-card"
SELETOR_TITULO = ".poly-component__title"


def criar_slug_categoria(categoria: str) -> str:
    """
    Transforma:

    Eletrônicos, Áudio e Vídeo
    em:
    eletronicos_audio_e_video
    """

    texto = unicodedata.normalize("NFKD", categoria)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    texto = texto.lower()

    caracteres = []

    for caractere in texto:
        if caractere.isalnum():
            caracteres.append(caractere)
        else:
            caracteres.append("_")

    slug = "".join(caracteres)

    while "__" in slug:
        slug = slug.replace("__", "_")

    return slug.strip("_")


class FiltroCategoriasMercadoLivre:
    """
    Controla o filtro de categorias do painel de afiliados.

    O Mercado Livre também possui um botão "Categorias" no cabeçalho.
    Por isso, este código prioriza o último controle visível com esse nome,
    que corresponde ao painel de filtros na estrutura observada.
    """

    def __init__(
        self,
        pagina: Page,
        tempo_espera_atualizacao: float = 3.0,
    ) -> None:
        self.pagina = pagina
        self.tempo_espera_atualizacao = tempo_espera_atualizacao

    def selecionar_categoria(self, categoria: str) -> None:
        if categoria not in CATEGORIAS_ALVO:
            raise ValueError(
                f"Categoria não configurada: {categoria}. "
                f"Permitidas: {', '.join(CATEGORIAS_ALVO)}"
            )

        print("\n" + "=" * 70)
        print(f"Aplicando categoria: {categoria}")
        print("=" * 70)

        self._voltar_ao_topo()

        assinatura_anterior = self._obter_assinatura_produtos()

        self._abrir_filtro_categorias()

        self._desmarcar_outras_categorias(
            categoria_a_manter=categoria,
        )

        opcao = self._localizar_opcao_categoria(categoria)

        if self._opcao_esta_marcada(opcao):
            print("A categoria já estava selecionada.")
        else:
            self._clicar_opcao(opcao)
            print("Categoria marcada no painel.")

        self._esperar_atualizacao(
            assinatura_anterior=assinatura_anterior,
        )

        self._voltar_ao_topo()

        quantidade = self.pagina.locator(SELETOR_CARD).count()

        print(f"Categoria aplicada: {categoria}")
        print(f"Cards carregados inicialmente: {quantidade}")

    def _abrir_filtro_categorias(self) -> None:
        """
        Localiza o controle de categorias do painel de afiliados.

        Existem dois textos "Categorias" na página.
        O último visível costuma ser o filtro correto.
        """

        controles = self.pagina.get_by_text(
            "Categorias",
            exact=True,
        )

        quantidade = controles.count()

        if quantidade == 0:
            raise RuntimeError(
                'Nenhum controle com o texto "Categorias" foi encontrado.'
            )

        candidatos_visiveis: list[Locator] = []

        for indice in range(quantidade):
            candidato = controles.nth(indice)

            try:
                if candidato.is_visible():
                    candidatos_visiveis.append(candidato)
            except Exception:
                continue

        if not candidatos_visiveis:
            raise RuntimeError(
                'O texto "Categorias" foi encontrado, mas nenhum está visível.'
            )

        controle_painel = candidatos_visiveis[-1]

        try:
            controle_painel.scroll_into_view_if_needed()
        except Exception:
            pass

        controle_painel.click(timeout=5000)

        self.pagina.get_by_text(
            CATEGORIAS_ALVO[0],
            exact=True,
        ).last.wait_for(
            state="visible",
            timeout=10000,
        )

    def _localizar_opcao_categoria(
        self,
        categoria: str,
    ) -> Locator:
        opcoes = self.pagina.get_by_text(
            categoria,
            exact=True,
        )

        quantidade = opcoes.count()

        if quantidade == 0:
            raise RuntimeError(
                f'A categoria "{categoria}" não apareceu no painel.'
            )

        for indice in reversed(range(quantidade)):
            opcao = opcoes.nth(indice)

            try:
                if opcao.is_visible():
                    return opcao
            except Exception:
                continue

        raise RuntimeError(
            f'A categoria "{categoria}" foi encontrada, '
            "mas nenhuma opção está visível."
        )

    def _desmarcar_outras_categorias(
        self,
        categoria_a_manter: str,
    ) -> None:
        for categoria in CATEGORIAS_ALVO:
            if categoria == categoria_a_manter:
                continue

            try:
                opcao = self._localizar_opcao_categoria(categoria)
            except RuntimeError:
                continue

            if self._opcao_esta_marcada(opcao):
                print(f"Desmarcando categoria anterior: {categoria}")
                self._clicar_opcao(opcao)
                time.sleep(1.0)

    def _opcao_esta_marcada(
        self,
        opcao: Locator,
    ) -> bool:
        checkbox = self._encontrar_checkbox(opcao)

        if checkbox is not None:
            try:
                return checkbox.is_checked()
            except Exception:
                pass

        atributos_possiveis = (
            "aria-checked",
            "aria-selected",
            "data-checked",
        )

        elementos_para_testar = [
            opcao,
            opcao.locator("xpath=.."),
            opcao.locator("xpath=../.."),
        ]

        for elemento in elementos_para_testar:
            try:
                for atributo in atributos_possiveis:
                    valor = elemento.get_attribute(atributo)

                    if valor and valor.lower() == "true":
                        return True

                classes = elemento.get_attribute("class") or ""
                classes = classes.lower()

                if any(
                    termo in classes
                    for termo in (
                        "checked",
                        "selected",
                        "active",
                    )
                ):
                    return True

            except Exception:
                continue

        return False

    def _encontrar_checkbox(
        self,
        opcao: Locator,
    ) -> Locator | None:
        localizadores = (
            opcao.locator(
                "xpath=ancestor::label[1]//input[@type='checkbox']"
            ),
            opcao.locator(
                "xpath=ancestor::*[1]//input[@type='checkbox']"
            ),
            opcao.locator(
                "xpath=ancestor::*[2]//input[@type='checkbox']"
            ),
        )

        for localizador in localizadores:
            try:
                if localizador.count() > 0:
                    return localizador.first
            except Exception:
                continue

        return None

    def _clicar_opcao(
        self,
        opcao: Locator,
    ) -> None:
        checkbox = self._encontrar_checkbox(opcao)

        if checkbox is not None:
            try:
                checkbox.click(
                    force=True,
                    timeout=5000,
                )
                return
            except Exception:
                pass

        try:
            opcao.click(timeout=5000)
            return
        except Exception:
            pass

        try:
            opcao.locator("xpath=ancestor::label[1]").click(
                force=True,
                timeout=5000,
            )
            return
        except Exception as erro:
            raise RuntimeError(
                "Não foi possível clicar na opção de categoria."
            ) from erro

    def _esperar_atualizacao(
        self,
        assinatura_anterior: tuple[str, ...],
    ) -> None:
        """
        Espera a lista de produtos mudar depois da seleção.

        Algumas atualizações do painel demoram alguns segundos.
        """

        prazo_final = time.monotonic() + 25

        while time.monotonic() < prazo_final:
            time.sleep(1.0)

            assinatura_atual = self._obter_assinatura_produtos()

            if (
                assinatura_atual
                and assinatura_atual != assinatura_anterior
            ):
                time.sleep(self.tempo_espera_atualizacao)
                return

        print(
            "Aviso: não foi possível confirmar a mudança pelos títulos. "
            "A coleta continuará com o estado atual da página."
        )

        time.sleep(self.tempo_espera_atualizacao)

    def _obter_assinatura_produtos(
        self,
        limite: int = 5,
    ) -> tuple[str, ...]:
        cards = self.pagina.locator(SELETOR_CARD)
        quantidade = min(cards.count(), limite)

        titulos: list[str] = []

        for indice in range(quantidade):
            card = cards.nth(indice)
            titulo = card.locator(SELETOR_TITULO).first

            try:
                if titulo.count() > 0:
                    texto = titulo.inner_text(
                        timeout=2000,
                    ).strip()

                    if texto:
                        titulos.append(texto)
            except Exception:
                continue

        return tuple(titulos)

    def _voltar_ao_topo(self) -> None:
        self.pagina.evaluate(
            """
            () => {
                window.scrollTo({
                    top: 0,
                    behavior: "instant"
                });
            }
            """
        )

        time.sleep(1.5)


def validar_categorias(
    categorias: Iterable[str],
) -> tuple[str, ...]:
    resultado = tuple(categorias)

    invalidas = [
        categoria
        for categoria in resultado
        if categoria not in CATEGORIAS_ALVO
    ]

    if invalidas:
        raise ValueError(
            "Categorias inválidas: "
            + ", ".join(invalidas)
        )

    return resultado