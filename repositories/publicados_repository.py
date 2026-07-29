import json
from pathlib import Path


class PublicadosRepository:

    def __init__(self, caminho_arquivo: str = "database/publicados.json") -> None:
        self.caminho_arquivo = Path(caminho_arquivo)

        self._criar_arquivo_se_necessario()

    def _criar_arquivo_se_necessario(self) -> None:
        self.caminho_arquivo.parent.mkdir(parents=True, exist_ok=True)

        if not self.caminho_arquivo.exists():
            self.caminho_arquivo.write_text("[]", encoding="utf-8")

    def buscar_links_publicados(self) -> list[str]:
        conteudo = self.caminho_arquivo.read_text(encoding="utf-8")

        return json.loads(conteudo)

    def ja_foi_publicada(self, link: str) -> bool:
        links_publicados = self.buscar_links_publicados()

        return link in links_publicados

    def marcar_como_publicada(self, link: str) -> None:
        links_publicados = self.buscar_links_publicados()

        if link in links_publicados:
            return

        links_publicados.append(link)

        conteudo_json = json.dumps(links_publicados, indent=4, ensure_ascii=False)

        self.caminho_arquivo.write_text(conteudo_json, encoding="utf-8")
